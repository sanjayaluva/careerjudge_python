"""Career Profiling computation engine.

Implements the SRS §5.1-5.3 algorithm with three modes:

  STANDARD UNRANKED (SRS §4.1, no RankDefinition):
    - mapping_score = max(0, MAX_MAPPING_SCORE - band_distance)
    - weight        = MappingCriterion.weight (default 1.0)
    - product_score = mapping_score x weight
    - max_product   = MAX_MAPPING_SCORE x weight
    - VMI           = (product_score / max_product) x 100

  STANDARD RANKED (SRS §4.1.3 + §4.1.4, RankDefinition without is_polar):
    - mapping_score = max(0, MAX_MAPPING_SCORE - band_distance)  [same as unranked]
    - weight        = RankValue.rank_value looked up by criterion.rank_order
    - product_score = mapping_score x weight
    - max_product   = MAX_MAPPING_SCORE x weight
    - VMI           = (product_score / max_product) x 100

  POLAR (SRS §4.2, RankDefinition with is_polar=True; PolarMatchRule table required):
    - match_value   = PolarMatchRule.match_value for (criterion_band, user_band)
                      [HM=5, MM=3, LM=1 — NOT band-distance based]
    - weight        = PolarRankValue.rank_value looked up by (match_code, rank_order)
    - product_score = match_value x weight
    - max_product   = MAX_POLAR_MATCH_VALUE x weight
    - VMI           = (product_score / max_product) x 100

PMI per assessment = (sum_product / (max_product + max_product/100)) x 100
FMI per career     = mean(PMI) across assessments

Reference: specs/05_profiling_configuration.json sections 4.1, 4.2, 5.1, 5.2, 5.3
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
    PolarMatchRule,
    PolarRankValue,
    ProfilingSolution,
    RankDefinition,
    SelectedAssessment,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# Standard mode: 5 = exact band match, decreasing by 1 per band of distance.
MAX_MAPPING_SCORE = 5
# Polar mode: HM=5 is the max possible match_value.
MAX_POLAR_MATCH_VALUE = 5


# ---------------------------------------------------------------------------
# Data classes (transparent intermediate state — easy to test)
# ---------------------------------------------------------------------------


@dataclass
class VariableResult:
    """Per-variable computation result for one (assessment, career) pair.

    Fields are unioned across the three modes so the dataclass can represent
    any of them. mode-specific fields:
      standard (unranked/ranked): mapping_score, criterion_band_number,
                                  candidate_band_number, distance
      polar:                     match_code, match_value
    """

    variable: str
    assessment_label: str
    mode: str  # "standard_unranked" | "standard_ranked" | "polar"
    criterion_band: str
    candidate_band: str
    # Standard-mode fields (None for polar)
    criterion_band_number: int | None = None
    candidate_band_number: int | None = None
    distance: int | None = None
    mapping_score: int | None = None
    # Polar-mode fields (None for standard)
    match_code: str | None = None
    match_value: int | None = None
    # Common aggregation fields
    weight: float = 1.0
    product_score: float = 0.0
    vmi: float = 0.0  # 0-100


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
    career_stream: str = ""
    career_code: str = ""
    assessments: list[AssessmentResult] = field(default_factory=list)
    fmi: float | None = None  # 0-100, None if no PMIs computed
    vmi_overall: float | None = None  # mean of per-variable VMIs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_match_indices(solution: ProfilingSolution, candidate: User) -> list[MatchIndex]:
    """Compute and persist MatchIndex records for a candidate against every
    career defined in the solution's mapping_criteria.

    Returns the list of saved MatchIndex records. Records are skipped (and
    omitted from the response) when no variable is scorable for that career.
    """
    # Each criterion row carries (career_title, career_stream, career_code).
    # Group by (career_title, career_stream, career_code) so the same title in
    # different streams is treated as separate careers.
    careers = (
        solution.mapping_criteria.values("career_title", "career_stream", "career_code")
        .distinct()
        .order_by("career_stream", "career_title")
    )
    saved: list[MatchIndex] = []
    for career in careers:
        result = _compute_for_career(
            solution,
            candidate,
            career["career_title"],
            career["career_stream"],
            career["career_code"],
        )
        if result.fmi is None:
            logger.info(
                "Skipping MatchIndex for solution=%s candidate=%s career=%r — "
                "no scorable variables (no completed sessions or missing config).",
                solution.id,
                candidate.id,
                career["career_title"],
            )
            continue
        mi = _upsert_match_index(solution, candidate, result)
        saved.append(mi)
    return saved


# ---------------------------------------------------------------------------
# Internal: per-career computation
# ---------------------------------------------------------------------------


def _compute_for_career(
    solution: ProfilingSolution,
    candidate: User,
    career_title: str,
    career_stream: str = "",
    career_code: str = "",
) -> CareerResult:
    """Compute VMI, PMI per assessment, then FMI as average of PMIs."""
    criteria_qs = (
        solution.mapping_criteria.filter(career_title=career_title)
        .select_related("section")
        .order_by("section__level", "section__order")
    )
    result = CareerResult(
        career_title=career_title,
        career_stream=career_stream,
        career_code=career_code,
    )

    for sa in solution.selected_assessments.all().order_by("order"):
        ar = AssessmentResult(assessment_label=sa.label)
        session = _get_completed_session(sa.assessment_id, candidate.id)

        # Preload the RankDefinition (if any) once per selected_assessment.
        rank_def: RankDefinition | None = getattr(sa, "rank_definition", None)
        rank_values_by_order: dict[int, float] = {}
        if rank_def and not rank_def.is_polar:
            rank_values_by_order = {
                rv.rank_order: rv.rank_value for rv in rank_def.rank_values.all()
            }

        for criterion in criteria_qs:
            vr = _compute_variable(sa, session, criterion, rank_def, rank_values_by_order)
            if vr is not None:
                ar.variables.append(vr)

        # Aggregate PMI for this assessment
        if ar.variables:
            ar.sum_product = sum(v.product_score for v in ar.variables)
            ar.max_product = sum(_max_product_for(v) for v in ar.variables)
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


def _max_product_for(v: VariableResult) -> float:
    """Return the maximum possible product_score for a variable.

    For standard modes: MAX_MAPPING_SCORE x weight.
    For polar mode:     MAX_POLAR_MATCH_VALUE x weight.
    """
    base = MAX_POLAR_MATCH_VALUE if v.mode == "polar" else MAX_MAPPING_SCORE
    return base * v.weight


def _compute_variable(
    sa: SelectedAssessment,
    session: AssessmentSession | None,
    criterion: MappingCriterion,
    rank_def: RankDefinition | None,
    rank_values_by_order: dict[int, float],
) -> VariableResult | None:
    """Compute the per-variable mapping score, product, and VMI.

    Dispatches to _compute_standard_variable or _compute_polar_variable based
    on whether the selected_assessment has a polar RankDefinition.
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

    if rank_def is not None and rank_def.is_polar:
        return _compute_polar_variable(sa, band_def, criterion, candidate_band, rank_def)
    return _compute_standard_variable(
        sa, band_def, criterion, candidate_band, rank_def, rank_values_by_order
    )


# ---------------------------------------------------------------------------
# Standard mode (unranked + ranked)
# ---------------------------------------------------------------------------


def _compute_standard_variable(
    sa: SelectedAssessment,
    band_def: BandDefinition,
    criterion: MappingCriterion,
    candidate_band: Band,
    rank_def: RankDefinition | None,
    rank_values_by_order: dict[int, float],
) -> VariableResult | None:
    """Standard mode: mapping_score from band-number distance, weight from
    RankValue (ranked) or criterion.weight (unranked)."""
    criterion_band = band_def.bands.filter(band_code=criterion.criterion_band_code).first()
    if criterion_band is None:
        return None

    distance = abs(criterion_band.band_number - candidate_band.band_number)
    mapping_score = max(0, MAX_MAPPING_SCORE - distance)

    # Ranked mode: look up rank_value from chart by rank_order
    if rank_def is not None and criterion.rank_order is not None:
        weight = rank_values_by_order.get(criterion.rank_order)
        if weight is None:
            # rank_order out of range — misconfiguration, skip
            return None
        mode = "standard_ranked"
    else:
        # Unranked: use legacy weight field
        weight = float(criterion.weight) if criterion.weight else 1.0
        mode = "standard_unranked"

    product_score = mapping_score * weight
    max_product = MAX_MAPPING_SCORE * weight
    vmi = round((product_score / max_product) * 100, 2) if max_product > 0 else 0.0

    return VariableResult(
        variable=criterion.section.title,
        assessment_label=sa.label,
        mode=mode,
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
# Polar mode (SRS §4.2)
# ---------------------------------------------------------------------------


def _compute_polar_variable(
    sa: SelectedAssessment,
    band_def: BandDefinition,
    criterion: MappingCriterion,
    candidate_band: Band,
    rank_def: RankDefinition,
) -> VariableResult | None:
    """Polar mode: match_value from PolarMatchRule table, weight from
    PolarRankValue by (match_code, rank_order)."""
    # 1. Find the match rule for (criterion_band_code, user_band_code)
    rule = PolarMatchRule.objects.filter(
        band_definition=band_def,
        criterion_band_code=criterion.criterion_band_code,
        user_band_code=candidate_band.band_code,
    ).first()
    if rule is None:
        # No rule defined for this band combination — config incomplete
        return None

    # 2. Look up rank_value from the 2D polar chart
    if criterion.rank_order is None:
        # Polar mode requires rank_order on every criterion (SRS §4.2.3 says
        # polar ranking is NOT optional)
        return None
    polar_rv = PolarRankValue.objects.filter(
        rank_definition=rank_def,
        match_code=rule.match_code,
        rank_order=criterion.rank_order,
    ).first()
    if polar_rv is None:
        return None

    weight = float(polar_rv.rank_value)
    product_score = rule.match_value * weight
    max_product = MAX_POLAR_MATCH_VALUE * weight
    vmi = round((product_score / max_product) * 100, 2) if max_product > 0 else 0.0

    return VariableResult(
        variable=criterion.section.title,
        assessment_label=sa.label,
        mode="polar",
        criterion_band=criterion.criterion_band_code,
        candidate_band=candidate_band.band_code,
        match_code=rule.match_code,
        match_value=rule.match_value,
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
                    "mode": v.mode,
                    "criterion_band": v.criterion_band,
                    "candidate_band": v.candidate_band,
                    "criterion_band_number": v.criterion_band_number,
                    "candidate_band_number": v.candidate_band_number,
                    "distance": v.distance,
                    "mapping_score": v.mapping_score,
                    "match_code": v.match_code,
                    "match_value": v.match_value,
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
        career_code=result.career_code,
        defaults={
            "career_stream": result.career_stream,
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
