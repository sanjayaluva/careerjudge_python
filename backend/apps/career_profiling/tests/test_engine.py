"""Tests for the Career Profiling computation engine.

Covers the SRS §5.1-5.3 algorithm implemented in apps/career_profiling/engine.py:
  - Mapping Score (5 = exact band match, decreasing for distance)
  - Variable Mapping Index (VMI)
  - Profile Match Index (PMI) per assessment
  - Final Match Index (FMI) = average of PMIs

Test scenarios:
  1. Happy path: 2 assessments x 2 variables x 1 career, all exact matches
     → VMI=100 per variable, FMI≈99.01 (matches SRS example calculation)
  2. Distance-1 mismatch → mapping_score=4, VMI=80
  3. Multiple careers → one MatchIndex per career
  4. Weighted (rank) mode → product_score = mapping_score x weight
  5. Missing session → gracefully skipped
  6. Missing band_definition → variable skipped
  7. Idempotency: calling twice updates the existing record (no duplicates)
"""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import (
    Assessment,
    AssessmentSection,
    AssessmentSession,
    SectionScore,
)
from apps.career_profiling.engine import compute_match_indices
from apps.career_profiling.models import (
    Band,
    BandDefinition,
    MappingCriterion,
    MatchIndex,
    ProfilingSolution,
    SelectedAssessment,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_assessment(title="Test Assessment"):
    return Assessment.objects.create(
        title=title,
        objective="obj",
        status="published",
    )


def _make_section(assessment, title="Variable", level=1, order=1):
    return AssessmentSection.objects.create(
        assessment=assessment,
        title=title,
        level=level,
        order=order,
    )


def _make_completed_session(assessment, candidate):
    return AssessmentSession.objects.create(
        assessment=assessment,
        candidate=candidate,
        status="completed",
        total_score=0,
        max_score=0,
    )


def _set_section_score(session, section, percentage):
    """Create/update a SectionScore with the given percentage.

    The SectionScore.save() auto-computes percentage from raw/max, so we
    derive raw_score from the percentage to get the desired value.
    """
    ss, _ = SectionScore.objects.update_or_create(
        session=session,
        section=section,
        defaults={
            "raw_score": float(percentage),
            "max_score": 100.0,
        },
    )
    # Save triggers percentage recompute
    ss.save()
    return ss


def _make_band_definition(selected_assessment, section):
    return BandDefinition.objects.create(
        selected_assessment=selected_assessment,
        section=section,
    )


def _make_band(band_def, number, range_min, range_max, code):
    return Band.objects.create(
        band_definition=band_def,
        band_number=number,
        range_min=range_min,
        range_max=range_max,
        band_code=code,
    )


def _setup_standard_bands(band_def):
    """Create the standard 5-band config used in the SRS examples:
    1=Low(0-20), 2=Below-Avg(20-40), 3=Average(40-60), 4=Above-Avg(60-80), 5=High(80-100)
    """
    _make_band(band_def, 1, 0, 20, "L")
    _make_band(band_def, 2, 20, 40, "BL")
    _make_band(band_def, 3, 40, 60, "AVG")
    _make_band(band_def, 4, 60, 80, "AH")
    _make_band(band_def, 5, 80, 100, "H")
    return band_def


def _make_solution_with_assessments(candidate, num_assessments=2):
    """Create a published ProfilingSolution with N selected assessments + a
    session per assessment. Returns (solution, [(selected_assessment, session), ...]).
    """
    solution = ProfilingSolution.objects.create(
        title="Test Solution",
        purpose="test",
        description="test",
        status="published",
        created_by=candidate,
    )
    pairs = []
    for i in range(num_assessments):
        a = _make_assessment(title=f"Assessment {i + 1}")
        sa = SelectedAssessment.objects.create(
            solution=solution,
            assessment=a,
            label=f"A{i + 1}",
            order=i,
        )
        session = _make_completed_session(a, candidate)
        pairs.append((sa, session))
    return solution, pairs


# ---------------------------------------------------------------------------
# Happy path — exact match everywhere
# ---------------------------------------------------------------------------


def test_happy_path_exact_match_all_variables():
    """All variables match the criterion exactly → VMI=100 per variable,
    PMI≈99.01 per assessment, FMI≈99.01 across 2 assessments.

    SRS §5.1.2 PMI formula: PMI = (sum_product / (max_product + max_product/100)) x 100
      For 2 variables x mapping_score 5 = sum_product 10
      max_product = 5 x 2 = 10
      adjusted_max = 10 + 0.10 = 10.10
      PMI = (10 / 10.10) x 100 = 99.0099...
      FMI = (99.01 + 99.01) / 2 = 99.01
    """
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=2)

    # 2 sections per assessment
    sections_by_sa = {}
    for sa, _ in pairs:
        s1 = _make_section(sa.assessment, title=f"{sa.label}-V1", order=1)
        s2 = _make_section(sa.assessment, title=f"{sa.label}-V2", order=2)
        sections_by_sa[sa.id] = [s1, s2]
        bd1 = _make_band_definition(sa, s1)
        bd2 = _make_band_definition(sa, s2)
        _setup_standard_bands(bd1)
        _setup_standard_bands(bd2)

    # Candidate scores 90% everywhere → band 5 (High) everywhere
    for sa, session in pairs:
        for s in sections_by_sa[sa.id]:
            _set_section_score(session, s, 90.0)

    # Criterion = High (band 5) for every variable → exact match
    for sa, _ in pairs:
        for s in sections_by_sa[sa.id]:
            MappingCriterion.objects.create(
                solution=solution,
                career_title="Programmer",
                section=s,
                criterion_band_code="H",
                weight=1.0,
            )

    results = compute_match_indices(solution, candidate)
    assert len(results) == 1
    mi = results[0]
    assert mi.career_title == "Programmer"
    assert mi.variable_mapping_index == 100.0
    assert mi.final_match_index == pytest.approx(99.01, abs=0.01)
    # 4 variables total (2 per assessment x 2 assessments)
    assert len(mi.variable_details) == 4
    for v in mi.variable_details:
        assert v["mapping_score"] == 5
        assert v["vmi"] == 100.0
        assert v["distance"] == 0


# ---------------------------------------------------------------------------
# Distance mismatch
# ---------------------------------------------------------------------------


def test_distance_1_mismatch_gives_mapping_score_4():
    """Candidate is one band away from criterion → mapping_score=4, VMI=80."""
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=1)
    sa, session = pairs[0]
    s = _make_section(sa.assessment, title="V1")
    bd = _make_band_definition(sa, s)
    _setup_standard_bands(bd)

    # Candidate at 50% → band 3 (Average)
    _set_section_score(session, s, 50.0)
    # Criterion = band 4 (Above-Avg, code 'AH') → distance 1
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Analyst",
        section=s,
        criterion_band_code="AH",
        weight=1.0,
    )

    results = compute_match_indices(solution, candidate)
    assert len(results) == 1
    mi = results[0]
    v = mi.variable_details[0]
    assert v["distance"] == 1
    assert v["mapping_score"] == 4
    assert v["vmi"] == 80.0


def test_distance_5_or_more_gives_mapping_score_0():
    """Distance ≥ 5 → mapping_score clamped to 0 (not negative)."""
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=1)
    sa, session = pairs[0]
    s = _make_section(sa.assessment, title="V1")
    bd = _make_band_definition(sa, s)
    _setup_standard_bands(bd)

    # Candidate at 10% → band 1 (Low)
    _set_section_score(session, s, 10.0)
    # Criterion = band 5 (High) → distance 4 → score 1
    # Add an extra band to push distance beyond 5
    _make_band(bd, 6, 100, 100, "XH")
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Hard Role",
        section=s,
        criterion_band_code="XH",  # band 6, distance 5
        weight=1.0,
    )

    results = compute_match_indices(solution, candidate)
    mi = results[0]
    v = mi.variable_details[0]
    assert v["distance"] == 5
    assert v["mapping_score"] == 0  # max(0, 5-5) = 0


# ---------------------------------------------------------------------------
# Multiple careers
# ---------------------------------------------------------------------------


def test_multiple_careers_produces_one_match_index_each():
    """2 careers → 2 MatchIndex records, each with its own FMI."""
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=1)
    sa, session = pairs[0]
    s = _make_section(sa.assessment, title="V1")
    bd = _make_band_definition(sa, s)
    _setup_standard_bands(bd)

    # Candidate at 50% → band 3 (Average)
    _set_section_score(session, s, 50.0)

    # Career A: criterion = band 3 (exact) → score 5
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Career A",
        section=s,
        criterion_band_code="AVG",
        weight=1.0,
    )
    # Career B: criterion = band 5 (distance 2) → score 3
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Career B",
        section=s,
        criterion_band_code="H",
        weight=1.0,
    )

    results = compute_match_indices(solution, candidate)
    assert len(results) == 2
    by_career = {r.career_title: r for r in results}
    assert by_career["Career A"].variable_details[0]["mapping_score"] == 5
    assert by_career["Career B"].variable_details[0]["mapping_score"] == 3
    # Career A has higher FMI than Career B
    assert by_career["Career A"].final_match_index > by_career["Career B"].final_match_index


# ---------------------------------------------------------------------------
# Weighted (rank) mode
# ---------------------------------------------------------------------------


def test_weighted_mode_uses_product_score():
    """With weight (rank_value) > 1, product_score = mapping_score x weight,
    but VMI stays 100 for exact match (because max_product also scales).

    The PMI formula adjusts max_product with the weights, so an exact match
    across all variables still gives PMI≈99.01 regardless of weight.
    """
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=1)
    sa, session = pairs[0]
    s1 = _make_section(sa.assessment, title="V1", order=1)
    s2 = _make_section(sa.assessment, title="V2", order=2)
    bd1 = _make_band_definition(sa, s1)
    bd2 = _make_band_definition(sa, s2)
    _setup_standard_bands(bd1)
    _setup_standard_bands(bd2)

    # Both variables at 90% → band 5
    _set_section_score(session, s1, 90.0)
    _set_section_score(session, s2, 90.0)

    # Criterion = band 5 (exact) for both, but weights differ
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Weighted Role",
        section=s1,
        criterion_band_code="H",
        weight=2.0,  # rank_value = 2.0
    )
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Weighted Role",
        section=s2,
        criterion_band_code="H",
        weight=1.5,
    )

    results = compute_match_indices(solution, candidate)
    mi = results[0]
    # Each variable: product = 5 x weight, max = 5 x weight → VMI = 100
    for v in mi.variable_details:
        assert v["mapping_score"] == 5
        assert v["vmi"] == 100.0
    # sum_product = 5x2 + 5x1.5 = 17.5
    # max_product = 5x2 + 5x1.5 = 17.5
    # adjusted_max = 17.5 + 0.175 = 17.675
    # PMI = (17.5 / 17.675) x 100 ≈ 99.01
    assert mi.final_match_index == pytest.approx(99.01, abs=0.02)


def test_weighted_mode_distance_mismatch_penalises_more():
    """With weight=2, a distance-1 mismatch produces product_score=8 vs max=10
    → VMI = 80 (same as unweighted, but the PMI impact is larger because the
    weighted variable contributes more to max_product)."""
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=1)
    sa, session = pairs[0]
    s1 = _make_section(sa.assessment, title="V1", order=1)
    s2 = _make_section(sa.assessment, title="V2", order=2)
    bd1 = _make_band_definition(sa, s1)
    bd2 = _make_band_definition(sa, s2)
    _setup_standard_bands(bd1)
    _setup_standard_bands(bd2)

    # V1: 90% (band 5), V2: 50% (band 3)
    _set_section_score(session, s1, 90.0)
    _set_section_score(session, s2, 50.0)

    # V1: criterion band 5 (exact), weight 1.0
    # V2: criterion band 4 (distance 1), weight 2.0 (more important)
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s1,
        criterion_band_code="H",
        weight=1.0,
    )
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s2,
        criterion_band_code="AH",  # band 4, candidate is band 3 → distance 1
        weight=2.0,
    )

    mi = compute_match_indices(solution, candidate)[0]
    v1, v2 = mi.variable_details
    assert v1["mapping_score"] == 5
    assert v2["mapping_score"] == 4
    assert v2["product_score"] == 8.0  # 4 x 2.0
    assert v2["vmi"] == 80.0  # 8 / (5x2) x 100
    # sum_product = 5x1 + 4x2 = 13
    # max_product = 5x1 + 5x2 = 15
    # adjusted_max = 15 + 0.15 = 15.15
    # PMI = (13 / 15.15) x 100 ≈ 85.81
    assert mi.final_match_index == pytest.approx(85.81, abs=0.1)


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


def test_missing_session_skips_variable():
    """If the candidate has no completed session for the assessment, the
    variable is skipped. If NO variable is scorable, no MatchIndex is created.
    """
    candidate = UserFactory()
    solution = ProfilingSolution.objects.create(
        title="S",
        status="published",
        created_by=candidate,
    )
    a = _make_assessment()
    sa = SelectedAssessment.objects.create(solution=solution, assessment=a, label="A1")
    s = _make_section(a, title="V1")
    bd = _make_band_definition(sa, s)
    _setup_standard_bands(bd)
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s,
        criterion_band_code="H",
        weight=1.0,
    )
    # No AssessmentSession created for this candidate
    results = compute_match_indices(solution, candidate)
    assert results == []  # nothing scorable → nothing saved


def test_missing_band_definition_skips_variable():
    """A variable with mapping_criterion but no band_definition is skipped."""
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=1)
    sa, session = pairs[0]
    s1 = _make_section(sa.assessment, title="V1", order=1)
    s2 = _make_section(sa.assessment, title="V2", order=2)
    # Only V1 gets a band_definition; V2 doesn't
    bd1 = _make_band_definition(sa, s1)
    _setup_standard_bands(bd1)
    _set_section_score(session, s1, 90.0)
    _set_section_score(session, s2, 90.0)
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s1,
        criterion_band_code="H",
        weight=1.0,
    )
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s2,  # no band_definition → skipped
        criterion_band_code="H",
        weight=1.0,
    )
    mi = compute_match_indices(solution, candidate)[0]
    assert len(mi.variable_details) == 1
    assert mi.variable_details[0]["variable"] == "V1"


def test_percentage_outside_band_range_skips_variable():
    """If the candidate's percentage doesn't fall into any band (config gap),
    the variable is skipped rather than crashing.
    """
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=1)
    sa, session = pairs[0]
    s = _make_section(sa.assessment, title="V1")
    bd = _make_band_definition(sa, s)
    # Gap: bands cover 0-40 and 60-100, but not 40-60
    _make_band(bd, 1, 0, 40, "L")
    _make_band(bd, 2, 60, 100, "H")
    _set_section_score(session, s, 50.0)  # falls in the gap
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s,
        criterion_band_code="H",
        weight=1.0,
    )
    results = compute_match_indices(solution, candidate)
    assert results == []  # nothing scorable


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_compute_is_idempotent_updates_existing_record():
    """Calling compute twice for the same (solution, candidate, career) does
    NOT create duplicate MatchIndex rows — the existing row is updated."""
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=1)
    sa, session = pairs[0]
    s = _make_section(sa.assessment, title="V1")
    bd = _make_band_definition(sa, s)
    _setup_standard_bands(bd)
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s,
        criterion_band_code="H",
        weight=1.0,
    )
    # First computation at 90% → exact match
    _set_section_score(session, s, 90.0)
    mi1 = compute_match_indices(solution, candidate)[0]
    assert mi1.variable_details[0]["mapping_score"] == 5

    # Re-score to 50% (band 3) → distance 2, score 3
    _set_section_score(session, s, 50.0)
    mi2 = compute_match_indices(solution, candidate)[0]

    assert MatchIndex.objects.filter(solution=solution, candidate=candidate).count() == 1
    assert mi1.id == mi2.id  # same row, updated in place
    assert mi2.variable_details[0]["mapping_score"] == 3
    # mi1 in DB is also updated (refresh to confirm)
    mi1.refresh_from_db()
    assert mi1.variable_details[0]["mapping_score"] == 3


# ---------------------------------------------------------------------------
# Cross-assessment FMI
# ---------------------------------------------------------------------------


def test_fmi_is_average_of_assessment_pmis():
    """Two assessments with different PMIs → FMI is the arithmetic mean.

    A1: candidate scores 90% (band 5), criterion band 5 → exact → PMI≈99.01
    A2: candidate scores 50% (band 3), criterion band 5 → distance 2 → score 3
        sum_product = 3, max_product = 5, adjusted = 5.05
        PMI = (3 / 5.05) x 100 ≈ 59.41
    FMI = (99.01 + 59.41) / 2 ≈ 79.21
    """
    candidate = UserFactory()
    solution, pairs = _make_solution_with_assessments(candidate, num_assessments=2)
    (sa1, session1), (sa2, session2) = pairs

    s1 = _make_section(sa1.assessment, title="A1-V1")
    s2 = _make_section(sa2.assessment, title="A2-V1")
    bd1 = _make_band_definition(sa1, s1)
    bd2 = _make_band_definition(sa2, s2)
    _setup_standard_bands(bd1)
    _setup_standard_bands(bd2)

    _set_section_score(session1, s1, 90.0)  # band 5
    _set_section_score(session2, s2, 50.0)  # band 3

    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s1,
        criterion_band_code="H",  # band 5 → exact
        weight=1.0,
    )
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s2,
        criterion_band_code="H",  # band 5 → distance 2
        weight=1.0,
    )

    mi = compute_match_indices(solution, candidate)[0]
    # Find per-assessment details
    a1_vars = [v for v in mi.variable_details if v["assessment"] == "A1"]
    a2_vars = [v for v in mi.variable_details if v["assessment"] == "A2"]
    assert a1_vars[0]["pmi"] == pytest.approx(99.01, abs=0.02)
    assert a2_vars[0]["pmi"] == pytest.approx(59.41, abs=0.1)
    # FMI = average of the two PMIs
    assert mi.final_match_index == pytest.approx(
        (a1_vars[0]["pmi"] + a2_vars[0]["pmi"]) / 2, abs=0.05
    )
