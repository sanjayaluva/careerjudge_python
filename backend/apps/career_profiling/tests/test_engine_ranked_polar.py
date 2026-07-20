"""Tests for ranked-mode and polar-mode Career Profiling computation.

Covers the SRS §4.1.3 (standard rank system) and §4.2 (polar assessment)
paths of the engine, complementing test_engine.py which covers the
unranked standard path.
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
    PolarMatchRule,
    PolarRankValue,
    ProfilingSolution,
    RankDefinition,
    RankValue,
    SelectedAssessment,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_standard_5_band_config(band_def):
    """5-band config: 1=L(0-20), 2=BL(20-40), 3=AVG(40-60), 4=AH(60-80), 5=H(80-100)."""
    for n, lo, hi, code in [
        (1, 0, 20, "L"),
        (2, 20, 40, "BL"),
        (3, 40, 60, "AVG"),
        (4, 60, 80, "AH"),
        (5, 80, 100, "H"),
    ]:
        Band.objects.create(
            band_definition=band_def,
            band_number=n,
            range_min=lo,
            range_max=hi,
            band_code=code,
        )


def _make_polar_3_band_config(band_def):
    """3-band polar config: 1=C1(0-20), 2=M(20-80), 3=C2(80-100)."""
    Band.objects.create(
        band_definition=band_def, band_number=1, range_min=0, range_max=20, band_code="C1"
    )
    Band.objects.create(
        band_definition=band_def, band_number=2, range_min=20, range_max=80, band_code="M"
    )
    Band.objects.create(
        band_definition=band_def, band_number=3, range_min=80, range_max=100, band_code="C2"
    )


def _setup_solution_with_assessment(candidate, num_assessments=1, polar=False):
    solution = ProfilingSolution.objects.create(
        title="S",
        status="published",
        has_polar_assessment=polar,
        created_by=candidate,
    )
    pairs = []
    for i in range(num_assessments):
        a = Assessment.objects.create(title=f"A{i + 1}", status="published")
        sa = SelectedAssessment.objects.create(
            solution=solution, assessment=a, label=f"A{i + 1}", is_polar=polar, order=i
        )
        session = AssessmentSession.objects.create(
            assessment=a, candidate=candidate, status="completed"
        )
        pairs.append((sa, session))
    return solution, pairs


# ---------------------------------------------------------------------------
# Standard ranked mode (SRS §4.1.3 + §4.1.4)
# ---------------------------------------------------------------------------


def test_standard_ranked_mode_uses_rank_value_from_chart():
    """When a RankDefinition exists for the selected_assessment, the engine
    looks up rank_value by MappingCriterion.rank_order instead of using
    criterion.weight directly.

    Setup: 2 variables, both exact-match (band 5 vs band 5).
      V1: rank_order=1 -> rank_value 2.0
      V2: rank_order=2 -> rank_value 1.8

    Expected:
      V1: product = 5 x 2.0 = 10, max = 5 x 2.0 = 10 -> VMI = 100
      V2: product = 5 x 1.8 = 9,  max = 5 x 1.8 = 9  -> VMI = 100
      sum_product = 19, max_product = 19
      adjusted_max = 19 + 0.19 = 19.19
      PMI = (19 / 19.19) x 100 ~ 99.01
    """
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1)
    sa, session = pairs[0]

    s1 = AssessmentSection.objects.create(assessment=sa.assessment, title="V1", level=1, order=1)
    s2 = AssessmentSection.objects.create(assessment=sa.assessment, title="V2", level=1, order=2)
    bd1 = BandDefinition.objects.create(selected_assessment=sa, section=s1)
    bd2 = BandDefinition.objects.create(selected_assessment=sa, section=s2)
    _make_standard_5_band_config(bd1)
    _make_standard_5_band_config(bd2)

    SectionScore.objects.create(session=session, section=s1, raw_score=90, max_score=100)
    SectionScore.objects.create(session=session, section=s2, raw_score=90, max_score=100)

    # Rank chart with 2 entries: Rank1=2.0, Rank2=1.8 (matches SRS §4.1.3 sample)
    rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=False)
    RankValue.objects.create(rank_definition=rank_def, rank_order=1, rank_value=2.0)
    RankValue.objects.create(rank_definition=rank_def, rank_order=2, rank_value=1.8)

    MappingCriterion.objects.create(
        solution=solution,
        career_title="Prog",
        section=s1,
        criterion_band_code="H",
        rank_order=1,
        weight=1.0,  # ignored because rank_order is set + rank_def exists
    )
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Prog",
        section=s2,
        criterion_band_code="H",
        rank_order=2,
        weight=1.0,
    )

    mi = compute_match_indices(solution, candidate)[0]
    v1, v2 = mi.variable_details
    assert v1["mode"] == "standard_ranked"
    assert v2["mode"] == "standard_ranked"
    assert v1["weight"] == 2.0
    assert v2["weight"] == 1.8
    assert v1["product_score"] == 10.0
    assert v2["product_score"] == 9.0
    assert v1["vmi"] == 100.0
    assert v2["vmi"] == 100.0
    assert mi.final_match_index == pytest.approx(99.01, abs=0.02)


def test_standard_ranked_mode_with_distance_mismatch():
    """In ranked mode, a distance-1 mismatch gives mapping_score=4 and the
    VMI drops to 80 (regardless of weight, since weight scales both product
    and max equally)."""
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1)
    sa, session = pairs[0]

    s = AssessmentSection.objects.create(assessment=sa.assessment, title="V1", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    _make_standard_5_band_config(bd)

    # Candidate at 50% -> band 3 (AVG)
    SectionScore.objects.create(session=session, section=s, raw_score=50, max_score=100)

    rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=False)
    RankValue.objects.create(rank_definition=rank_def, rank_order=1, rank_value=2.0)

    # Criterion = band 4 (AH) -> distance 1 -> mapping_score 4
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Analyst",
        section=s,
        criterion_band_code="AH",
        rank_order=1,
    )

    mi = compute_match_indices(solution, candidate)[0]
    v = mi.variable_details[0]
    assert v["mode"] == "standard_ranked"
    assert v["mapping_score"] == 4
    assert v["weight"] == 2.0
    assert v["product_score"] == 8.0  # 4 x 2.0
    assert v["vmi"] == 80.0  # 8 / (5 x 2.0) x 100


def test_rank_order_out_of_range_skips_variable():
    """If rank_order doesn't exist in the chart, the variable is skipped."""
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1)
    sa, session = pairs[0]
    s = AssessmentSection.objects.create(assessment=sa.assessment, title="V1", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    _make_standard_5_band_config(bd)
    SectionScore.objects.create(session=session, section=s, raw_score=90, max_score=100)

    rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=False)
    RankValue.objects.create(rank_definition=rank_def, rank_order=1, rank_value=2.0)
    # rank_order=99 doesn't exist in the chart
    MappingCriterion.objects.create(
        solution=solution,
        career_title="X",
        section=s,
        criterion_band_code="H",
        rank_order=99,
    )
    results = compute_match_indices(solution, candidate)
    assert results == []  # variable skipped, no FMI


# ---------------------------------------------------------------------------
# Polar mode (SRS §4.2)
# ---------------------------------------------------------------------------


def test_polar_mode_exact_match_gives_max_vmi():
    """Polar mode: criterion=C1, user=C1 -> HM (value 5) -> VMI = 100.

    Setup (per SRS §4.2.2 Social-Reserved example, simplified to 1 variable):
      Band config: C1(0-20), M(20-80), C2(80-100)
      Candidate scores 10% -> band C1
      Criterion band code = C1 -> match rule: criterion=C1, user=C1 -> HM, value 5
      Polar rank chart: HM + Rank1 -> 7.0
      Expected:
        product = match_value(5) x rank_value(7) = 35
        max     = MAX_POLAR_MATCH_VALUE(5) x rank_value(7) = 35
        VMI     = (35 / 35) x 100 = 100
    """
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1, polar=True)
    sa, session = pairs[0]
    s = AssessmentSection.objects.create(assessment=sa.assessment, title="SR", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    _make_polar_3_band_config(bd)

    # Candidate at 10% -> band C1
    SectionScore.objects.create(session=session, section=s, raw_score=10, max_score=100)

    # Polar match rules: 9 rules per SRS §4.2.2 (simplified — just the 3 perfect matches)
    PolarMatchRule.objects.create(
        band_definition=bd,
        criterion_band_code="C1",
        user_band_code="C1",
        match_code="HM",
        match_value=5,
    )
    PolarMatchRule.objects.create(
        band_definition=bd,
        criterion_band_code="M",
        user_band_code="M",
        match_code="HM",
        match_value=5,
    )
    PolarMatchRule.objects.create(
        band_definition=bd,
        criterion_band_code="C2",
        user_band_code="C2",
        match_code="HM",
        match_value=5,
    )

    # Polar rank chart (subset of SRS §4.2.3):
    # HM + Rank1 -> 7.0, MM + Rank1 -> 7.0, LM + Rank1 -> 3.0
    rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=True)
    for code, val in [("HM", 7.0), ("MM", 7.0), ("LM", 3.0)]:
        PolarRankValue.objects.create(
            rank_definition=rank_def, match_code=code, rank_order=1, rank_value=val
        )

    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s,
        criterion_band_code="C1",
        rank_order=1,
    )

    mi = compute_match_indices(solution, candidate)[0]
    v = mi.variable_details[0]
    assert v["mode"] == "polar"
    assert v["match_code"] == "HM"
    assert v["match_value"] == 5
    assert v["weight"] == 7.0
    assert v["product_score"] == 35.0  # 5 x 7
    assert v["vmi"] == 100.0
    # mapping_score should be None in polar mode (not band-distance based)
    assert v["mapping_score"] is None


def test_polar_mode_moderate_match_gives_lower_vmi():
    """Polar mode: criterion=C1, user=M -> MM (value 3) -> VMI = 60 (3/5 x 100)."""
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1, polar=True)
    sa, session = pairs[0]
    s = AssessmentSection.objects.create(assessment=sa.assessment, title="SR", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    _make_polar_3_band_config(bd)

    # Candidate at 50% -> band M (middle)
    SectionScore.objects.create(session=session, section=s, raw_score=50, max_score=100)

    # Match rule: criterion=C1, user=M -> MM, value 3
    PolarMatchRule.objects.create(
        band_definition=bd,
        criterion_band_code="C1",
        user_band_code="M",
        match_code="MM",
        match_value=3,
    )

    rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=True)
    PolarRankValue.objects.create(
        rank_definition=rank_def, match_code="MM", rank_order=1, rank_value=7.0
    )

    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s,
        criterion_band_code="C1",
        rank_order=1,
    )

    mi = compute_match_indices(solution, candidate)[0]
    v = mi.variable_details[0]
    assert v["match_code"] == "MM"
    assert v["match_value"] == 3
    # product = 3 x 7 = 21, max = 5 x 7 = 35, VMI = 21/35 x 100 = 60
    assert v["product_score"] == 21.0
    assert v["vmi"] == 60.0


def test_polar_mode_missing_match_rule_skips_variable():
    """If no PolarMatchRule exists for the (criterion, user) band pair, the
    variable is skipped — config is incomplete."""
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1, polar=True)
    sa, session = pairs[0]
    s = AssessmentSection.objects.create(assessment=sa.assessment, title="SR", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    _make_polar_3_band_config(bd)
    SectionScore.objects.create(session=session, section=s, raw_score=10, max_score=100)

    # No PolarMatchRule defined for (C1, C1)
    rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=True)
    PolarRankValue.objects.create(
        rank_definition=rank_def, match_code="HM", rank_order=1, rank_value=7.0
    )

    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role",
        section=s,
        criterion_band_code="C1",
        rank_order=1,
    )

    results = compute_match_indices(solution, candidate)
    assert results == []


def test_polar_mode_lm_inverts_rank_value_relationship():
    """SRS §4.2.3 quirk: for LM (Low Match), the rank_value INCREASES with
    rank_order. So LM+Rank1=3.0 but LM+Rank6=7.0 — opposite of HM.

    This test verifies the engine looks up rank_value by (match_code, rank_order)
    rather than just rank_order.
    """
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1, polar=True)
    sa, session = pairs[0]
    s = AssessmentSection.objects.create(assessment=sa.assessment, title="SR", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    _make_polar_3_band_config(bd)

    # Candidate at 10% -> C1
    SectionScore.objects.create(session=session, section=s, raw_score=10, max_score=100)

    # Match rule: criterion=M, user=C1 -> LM, value 1 (rule 8 in SRS example)
    PolarMatchRule.objects.create(
        band_definition=bd,
        criterion_band_code="M",
        user_band_code="C1",
        match_code="LM",
        match_value=1,
    )

    rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=True)
    # LM Rank1=3.0, LM Rank6=7.0 (per SRS §4.2.3 example)
    PolarRankValue.objects.create(
        rank_definition=rank_def, match_code="LM", rank_order=1, rank_value=3.0
    )
    PolarRankValue.objects.create(
        rank_definition=rank_def, match_code="LM", rank_order=6, rank_value=7.0
    )

    # Career A: criterion=M, rank_order=1 -> LM, value=1, rank_value=3.0
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role A",
        section=s,
        criterion_band_code="M",
        rank_order=1,
    )
    # Career B: criterion=M, rank_order=6 -> LM, value=1, rank_value=7.0
    MappingCriterion.objects.create(
        solution=solution,
        career_title="Role B",
        section=s,
        criterion_band_code="M",
        rank_order=6,
    )

    results = {r.career_title: r for r in compute_match_indices(solution, candidate)}
    a = results["Role A"].variable_details[0]
    b = results["Role B"].variable_details[0]
    # Same match_value (1) but different rank_value (3.0 vs 7.0)
    assert a["match_value"] == 1
    assert b["match_value"] == 1
    assert a["weight"] == 3.0
    assert b["weight"] == 7.0
    # VMI is the same (match_value / MAX_POLAR_MATCH_VALUE x 100 = 20)
    assert a["vmi"] == 20.0
    assert b["vmi"] == 20.0


# ---------------------------------------------------------------------------
# Career metadata propagation
# ---------------------------------------------------------------------------


def test_career_stream_and_code_propagate_to_match_index():
    """When MappingCriterion has career_stream + career_code, the MatchIndex
    is denormalised with those values so reports can group by stream."""
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1)
    sa, session = pairs[0]
    s = AssessmentSection.objects.create(assessment=sa.assessment, title="V1", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    _make_standard_5_band_config(bd)
    SectionScore.objects.create(session=session, section=s, raw_score=90, max_score=100)

    MappingCriterion.objects.create(
        solution=solution,
        career_stream="IT Sector",
        career_title="Programmer",
        career_code="ITCP",
        section=s,
        criterion_band_code="H",
        weight=1.0,
    )

    mi = compute_match_indices(solution, candidate)[0]
    assert mi.career_stream == "IT Sector"
    assert mi.career_title == "Programmer"
    assert mi.career_code == "ITCP"


def test_multiple_careers_in_different_streams():
    """Two careers with the same title but different streams are treated
    as separate careers and produce two MatchIndex records."""
    candidate = UserFactory()
    solution, pairs = _setup_solution_with_assessment(candidate, num_assessments=1)
    sa, session = pairs[0]
    s = AssessmentSection.objects.create(assessment=sa.assessment, title="V1", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    _make_standard_5_band_config(bd)
    SectionScore.objects.create(session=session, section=s, raw_score=90, max_score=100)

    # Same career_title but different stream + code
    MappingCriterion.objects.create(
        solution=solution,
        career_stream="IT",
        career_title="Analyst",
        career_code="ITA",
        section=s,
        criterion_band_code="H",
        weight=1.0,
    )
    MappingCriterion.objects.create(
        solution=solution,
        career_stream="Finance",
        career_title="Analyst",
        career_code="FA",
        section=s,
        criterion_band_code="H",
        weight=1.0,
    )

    results = compute_match_indices(solution, candidate)
    assert len(results) == 2
    streams = {r.career_stream for r in results}
    assert streams == {"IT", "Finance"}
