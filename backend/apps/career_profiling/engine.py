"""Career Profiling computation engine.

Implements the SRS §5.1-5.3 algorithm:
  1. Mapping Score per variable (5 = exact band match, decreasing for distance)
  2. Variable Mapping Index (VMI) per variable = (product_score / max_product) x 100
  3. Profile Match Index (PMI) per assessment per career
     = (sum_product / (max_product + max_product/100)) x 100
  4. Final Match Index (FMI) per career = average of PMIs across assessments

Two modes per SRS §5.1.1:
  - WITHOUT ranking: every variable's weight (rank_value) = 1.0
                     → product_score = mapping_score, max_product = 5 x n_vars
  - WITH ranking:    each variable has a rank_value (stored as MappingCriterion.weight)
                     → product_score = mapping_score x rank_value
                     → max_product = sum(5 x rank_value) across variables

Reference: specs/05_profiling_configuration.json sections 5.1.1, 5.1.2, 5.3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model

from apps.assessment.models import AssessmentSession

from .models import (
    Band,
    BandDefinition,
    MappingCriterion,
    MatchIndex,
    ProfilingSolution,
    SelectedAssessment,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# Per SRS §5.1.1: mapping score is 5 for an exact band match and decreases
# by 1 for each band of distance between the candidate's band and the
# criterion band. Minimum is 0.
MAX_MAPPING_SCORE = 5


# ---------------------------------------------------------------------------
# Data classes (for transparent intermediate state — easy to test)
# ---------------------------------------------------------------------------


@dataclass
class VariableResult:
    """Per-variable computation result for one (assessment, career) pair."""

    variable: str
    assessment_label: str
    criterion_band: str
    candidate_band: str
    criterion_band_number: int
    candidate_band_number: int
    distance: int
    mapping_score: int
    weight: float
    product_score: float
    vmi: float  # 0-100


@dataclass
class AssessmentResult:
    """Per-assessment aggregation for one career."""

    assessment_label: str
    variables: list[VariableResult] = field(default_factory=list)
    sum_product: float = 0.0
    max_product: float = 0.0
    pmi: float | None = None  # 0-100, None if no variables scored


@dataclass
class CareerResult:
    """Per-career aggregation across all selected assessments."""

    career_title: str
    assessments: list[AssessmentResult] = field(default_factory=list)
    fmi: float | None = None  # 0-100, None if no PMIs computed
    vmi_overall: float | None = None  # mean of per-variable VMIs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_match_indices(solution: ProfilingSolution, candidate: User) -> list[MatchIndex]:
    """Compute and persist MatchIndex records for a candidate against every
    career defined in the solution's mapping_criteria.

    Algorithm (SRS §5.1-5.3):
      For each career in mapping_criteria:
        For each selected_assessment:
          For each variable (section) that has both a band_definition and a
          mapping_criterion for this career:
            - Find the candidate's completed session for this assessment
            - Get the candidate's percentage score for this section
            - Find which band of the band_definition contains that percentage
            - Find the criterion band (by band_code) for this career+section
            - mapping_score = max(0, 5 - |criterion_band_num - candidate_band_num|)
            - product_score = mapping_score x weight (rank_value)
            - VMI = product_score / (5 x weight) x 100
          PMI = sum(product_scores) / (max_product + max_product/100) x 100
        FMI = average(PMIs across assessments)

    Upserts one MatchIndex per (solution, candidate, career_title) with the
    final VMI, FMI, and the per-variable breakdown stored as JSON.

    Returns the list of saved MatchIndex records.
    """
    careers = (
        solution.mapping_criteria.values_list("career_title", flat=True)
        .distinct()
        .order_by("career_title")
    )
    saved: list[MatchIndex] = []
    for career in careers:
        result = _compute_for_career(solution, candidate, career)
        if result.fmi is None:
            logger.info(
                "Skipping MatchIndex for solution=%s candidate=%s career=%r — "
                "no scorable variables (no completed sessions or missing config).",
                solution.id,
                candidate.id,
                career,
            )
            continue
        mi = _upsert_match_index(solution, candidate, result)
        saved.append(mi)
    return saved


# ---------------------------------------------------------------------------
# Internal: per-career computation
# ---------------------------------------------------------------------------


def _compute_for_career(
    solution: ProfilingSolution, candidate: User, career_title: str
) -> CareerResult:
    """Compute VMI, PMI per assessment, then FMI as average of PMIs."""
    criteria_qs = (
        solution.mapping_criteria.filter(career_title=career_title)
        .select_related("section")
        .order_by("section__level", "section__order")
    )
    result = CareerResult(career_title=career_title)

    for sa in solution.selected_assessments.all().order_by("order"):
        ar = AssessmentResult(assessment_label=sa.label)
        session = _get_completed_session(sa.assessment_id, candidate.id)

        for criterion in criteria_qs:
            vr = _compute_variable(sa, session, criterion)
            if vr is not None:
                ar.variables.append(vr)

        # Aggregate PMI for this assessment
        if ar.variables:
            ar.sum_product = sum(v.product_score for v in ar.variables)
            ar.max_product = sum(MAX_MAPPING_SCORE * v.weight for v in ar.variables)
            if ar.max_product > 0:
                adjusted_max = ar.max_product + (ar.max_product / 100)
                ar.pmi = round((ar.sum_product / adjusted_max) * 100, 2)
            else:
                ar.pmi = 0.0
        result.assessments.append(ar)

    # FMI = average of PMIs across assessments that produced a PMI
    pmis = [a.pmi for a in result.assessments if a.pmi is not None]
    if pmis:
        result.fmi = round(sum(pmis) / len(pmis), 2)

    # Overall VMI = mean of all per-variable VMIs
    all_vmis = [v.vmi for a in result.assessments for v in a.variables]
    if all_vmis:
        result.vmi_overall = round(sum(all_vmis) / len(all_vmis), 2)

    return result


def _compute_variable(
    sa: SelectedAssessment,
    session: AssessmentSession | None,
    criterion: MappingCriterion,
) -> VariableResult | None:
    """Compute the per-variable mapping score, product, and VMI.

    Returns None when the variable can't be scored for any of:
      - No band_definition for this assessment + section
      - No completed session for the candidate on this assessment
      - No SectionScore recorded for this section
      - No band contains the candidate's percentage (gap in config)
      - No band with the criterion's band_code exists
    """
    band_def = sa.band_definitions.filter(section=criterion.section).first()
    if not band_def:
        return None
    if session is None:
        return None
    ss = session.section_scores.filter(section=criterion.section).first()
    if ss is None or ss.percentage is None:
        return None
    candidate_band = _find_band_for_percentage(band_def, ss.percentage)
    if candidate_band is None:
        return None
    criterion_band = band_def.bands.filter(band_code=criterion.criterion_band_code).first()
    if criterion_band is None:
        return None

    distance = abs(criterion_band.band_number - candidate_band.band_number)
    mapping_score = max(0, MAX_MAPPING_SCORE - distance)
    weight = float(criterion.weight) if criterion.weight else 1.0
    product_score = mapping_score * weight
    max_product = MAX_MAPPING_SCORE * weight
    vmi = round((product_score / max_product) * 100, 2) if max_product > 0 else 0.0

    return VariableResult(
        variable=criterion.section.title,
        assessment_label=sa.label,
        criterion_band=criterion_band.band_code,
        candidate_band=candidate_band.band_code,
        criterion_band_number=criterion_band.band_number,
        candidate_band_number=candidate_band.band_number,
        distance=distance,
        mapping_score=mapping_score,
        weight=weight,
        product_score=product_score,
        vmi=vmi,
    )


# ---------------------------------------------------------------------------
# Internal: persistence
# ---------------------------------------------------------------------------


def _upsert_match_index(
    solution: ProfilingSolution, candidate: User, result: CareerResult
) -> MatchIndex:
    """Create or update the MatchIndex row with computed values + JSON breakdown."""
    variable_details: list[dict[str, Any]] = []
    for ar in result.assessments:
        for v in ar.variables:
            variable_details.append(
                {
                    "variable": v.variable,
                    "assessment": v.assessment_label,
                    "criterion_band": v.criterion_band,
                    "candidate_band": v.candidate_band,
                    "criterion_band_number": v.criterion_band_number,
                    "candidate_band_number": v.candidate_band_number,
                    "distance": v.distance,
                    "mapping_score": v.mapping_score,
                    "weight": v.weight,
                    "product_score": v.product_score,
                    "vmi": v.vmi,
                    "pmi": ar.pmi,
                }
            )

    mi, _ = MatchIndex.objects.update_or_create(
        solution=solution,
        candidate=candidate,
        career_title=result.career_title,
        defaults={
            "variable_mapping_index": result.vmi_overall,
            "final_match_index": result.fmi,
            "variable_details": variable_details,
        },
    )
    return mi


# ---------------------------------------------------------------------------
# Internal: helpers
# ---------------------------------------------------------------------------


def _get_completed_session(assessment_id: int, candidate_id: int) -> AssessmentSession | None:
    """Return the candidate's most recent completed session for an assessment."""
    return (
        AssessmentSession.objects.filter(
            assessment_id=assessment_id,
            candidate_id=candidate_id,
            status="completed",
        )
        .order_by("-completed_at")
        .first()
    )


def _find_band_for_percentage(band_def: BandDefinition, percentage: float) -> Band | None:
    """Find the band within a band_definition whose [range_min, range_max]
    contains the given percentage.

    Returns None if no band contains it (which usually means the band config
    has gaps — the caller should treat that as 'not scorable').
    """
    for band in band_def.bands.order_by("band_number"):
        if band.range_min <= percentage <= band.range_max:
            return band
    return None
