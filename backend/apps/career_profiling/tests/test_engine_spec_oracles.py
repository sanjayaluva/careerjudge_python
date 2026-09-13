"""Spec-oracle tests for the Career Profiling engine.

These tests reproduce the *worked examples* from
specs/05_profiling_configuration.json §5.1.2, §5.2.2 and §5.3 (the
"Computer Programmer" example) and assert the exact numbers the spec derives:

  Standard WITHOUT rank : summary 29, max 30, adjusted 30.3 -> PMI 95.7
  Standard WITH rank    : summary 43, max 45, adjusted 45.45 -> PMI 94.6
  Polar                 : summary 144, max 145, adjusted 146.45 -> PMI 98.33
  FMI (without rank)    : (95.7 + 98.33) / 2 = 97.01
  FMI (with rank)       : (94.6 + 98.33) / 2 = 96.46

These exercise:
  * C2 part 1 — the user-defined standard mapping-rule table (SRS §4.1.2)
  * H3       — the PMI Max-Mapping denominators (SRS §5.1.2 / §5.2.2), i.e.
               standard max = MAX(table value) x rank_value, polar max =
               MAX_POLAR_MATCH_VALUE x HM-rank-value at each rank_order.

Rounding note (asserted with a small tolerance on the final indices): the
spec quotes the *standard* PMI to one decimal (95.7 / 94.6) but the *polar*
PMI to two decimals (98.33). The engine rounds every PMI to two decimals, so
it derives 95.71 / 94.61 for the standard assessment. We therefore assert the
unambiguous intermediate values (summary mapping score, max mapping score,
adjusted max) EXACTLY — those are the real output of the H3 fix — and the
final PMI/FMI within 0.05.
"""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import (
    Assessment,
    AssessmentSection,
    AssessmentSession,
    SectionScore,
)
from apps.career_profiling.engine import _compute_for_career, compute_match_indices
from apps.career_profiling.models import (
    Band,
    BandDefinition,
    MappingCriterion,
    MappingRule,
    PolarMatchRule,
    PolarRankValue,
    ProfilingSolution,
    RankDefinition,
    RankValue,
    SelectedAssessment,
)

pytestmark = pytest.mark.django_db

CAREER = "Computer Programmer"

# SRS §4.1.3 sample Rank Order Chart (Rank1..Rank6)
STD_RANK_CHART = {1: 2.0, 2: 1.8, 3: 1.6, 4: 1.4, 5: 1.2, 6: 1.0}

# SRS §4.2.3 Rank Order & Match Value Chart
POLAR_RANK_CHART = {
    "HM": {1: 7.0, 2: 6.4, 3: 5.6, 4: 4.6, 5: 3.4, 6: 2.0},
    "MM": {1: 7.0, 2: 6.4, 3: 5.7, 4: 4.9, 5: 4.0, 6: 3.0},
    "LM": {1: 3.0, 2: 3.6, 3: 4.3, 4: 5.1, 5: 6.0, 6: 7.0},
}


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_solution(candidate):
    return ProfilingSolution.objects.create(
        title="Computer Programmer Solution",
        status="published",
        has_polar_assessment=True,
        created_by=candidate,
    )


def _band(bd, number, lo, hi, code):
    Band.objects.create(
        band_definition=bd, band_number=number, range_min=lo, range_max=hi, band_code=code
    )


# --- Standard (CAT) assessment reproducing SRS §5.1.1 -----------------------
#
# (variable, [bands], candidate_pct, criterion_code, [(crit, user, value)...],
#  rank_order)
#
# Each variable's mapping-rule table must have MAX value 5 (so the max mapping
# score per variable is 5, per H3). All variables map to 5 except Executive
# which maps to 4 — but Executive still carries a value-5 perfect-match rule so
# its table max stays 5.
_CAT_VARS = [
    ("Abstract", [(3, 40, 60, "ARM"), (4, 60, 80, "ARH1")], 70, "ARM", [("ARM", "ARH1", 5)], 4),
    ("Analytical", [(4, 60, 80, "ANH1")], 70, "ANH1", [("ANH1", "ANH1", 5)], 2),
    ("Verbal", [(3, 40, 60, "VRM"), (4, 60, 80, "VRH1")], 70, "VRM", [("VRM", "VRH1", 5)], 5),
    ("Quantitative", [(3, 40, 60, "QRM"), (4, 60, 80, "QRH1")], 70, "QRM", [("QRM", "QRH1", 5)], 3),
    ("Spatial", [(2, 20, 40, "SRL1")], 30, "SRL1", [("SRL1", "SRL1", 5)], 6),
    (
        "Executive",
        [(3, 40, 60, "EXM"), (4, 60, 80, "EXH1")],
        50,
        "EXH1",
        [("EXH1", "EXM", 4), ("EXH1", "EXH1", 5)],
        1,
    ),
]


def _build_cat_assessment(solution, candidate, order, ranked):
    """Build the standard CAT assessment (SRS §5.1.1). Returns SelectedAssessment."""
    a = Assessment.objects.create(title="CAT", status="published")
    sa = SelectedAssessment.objects.create(
        solution=solution, assessment=a, label="CAT", is_polar=False, order=order
    )
    session = AssessmentSession.objects.create(
        assessment=a, candidate=candidate, status="completed"
    )
    if ranked:
        rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=False)
        for ro, rv in STD_RANK_CHART.items():
            RankValue.objects.create(rank_definition=rank_def, rank_order=ro, rank_value=rv)

    for i, (title, bands, pct, crit_code, rules, rank_order) in enumerate(_CAT_VARS):
        section = AssessmentSection.objects.create(assessment=a, title=title, level=1, order=i + 1)
        bd = BandDefinition.objects.create(selected_assessment=sa, section=section)
        for number, lo, hi, code in bands:
            _band(bd, number, lo, hi, code)
        for crit, user, value in rules:
            MappingRule.objects.create(
                band_definition=bd,
                criterion_band_code=crit,
                user_band_code=user,
                value=value,
            )
        SectionScore.objects.create(session=session, section=section, raw_score=pct, max_score=100)
        MappingCriterion.objects.create(
            solution=solution,
            career_stream="IT Sector",
            career_title=CAREER,
            career_code="ITCP",
            section=section,
            criterion_band_code=crit_code,
            rank_order=rank_order if ranked else None,
        )
    return sa


# --- Polar (CIA) assessment reproducing SRS §5.2.1 --------------------------
#
# (variable, [bands], candidate_pct, criterion_code, user_code, match_code,
#  match_value, rank_order)
_CIA_VARS = [
    ("Social-Reserved", [(1, 0, 20, "SRC1")], 10, "SRC1", "SRC1", "HM", 5, 5),
    ("Numerical-Verbal", [(1, 0, 20, "NVC1")], 10, "NVC1", "NVC1", "HM", 5, 4),
    ("Serial-Systemic", [(1, 0, 20, "SSC1")], 10, "SSC1", "SSC1", "HM", 5, 3),
    ("Conventional-Investigative", [(1, 0, 20, "CIC1")], 10, "CIC1", "CIC1", "HM", 5, 1),
    ("Enterprising-Aesthetic", [(1, 0, 20, "EAC1")], 10, "EAM", "EAC1", "MM", 3, 6),
    ("Mental-Physical", [(2, 20, 80, "MPM")], 50, "MPM", "MPM", "HM", 5, 2),
]


def _build_cia_assessment(solution, candidate, order):
    """Build the polar CIA assessment (SRS §5.2.1). Returns SelectedAssessment."""
    a = Assessment.objects.create(title="CIA", status="published")
    sa = SelectedAssessment.objects.create(
        solution=solution, assessment=a, label="CIA", is_polar=True, order=order
    )
    session = AssessmentSession.objects.create(
        assessment=a, candidate=candidate, status="completed"
    )
    rank_def = RankDefinition.objects.create(selected_assessment=sa, is_polar=True)
    for code, by_order in POLAR_RANK_CHART.items():
        for ro, rv in by_order.items():
            PolarRankValue.objects.create(
                rank_definition=rank_def, match_code=code, rank_order=ro, rank_value=rv
            )

    for i, (title, bands, pct, crit_code, user_code, mcode, mval, rank_order) in enumerate(
        _CIA_VARS
    ):
        section = AssessmentSection.objects.create(assessment=a, title=title, level=1, order=i + 1)
        bd = BandDefinition.objects.create(selected_assessment=sa, section=section)
        for number, lo, hi, code in bands:
            _band(bd, number, lo, hi, code)
        PolarMatchRule.objects.create(
            band_definition=bd,
            criterion_band_code=crit_code,
            user_band_code=user_code,
            match_code=mcode,
            match_value=mval,
        )
        SectionScore.objects.create(session=session, section=section, raw_score=pct, max_score=100)
        MappingCriterion.objects.create(
            solution=solution,
            career_stream="IT Sector",
            career_title=CAREER,
            career_code="ITCP",
            section=section,
            criterion_band_code=crit_code,
            rank_order=rank_order,
        )
    return sa


def _assessment_result(result, label):
    return next(a for a in result.assessments if a.assessment_label == label)


# ---------------------------------------------------------------------------
# Standard PMI oracles (SRS §5.1.2)
# ---------------------------------------------------------------------------


def test_standard_without_rank_pmi_oracle():
    """SRS §5.1.2: summary 29, max 30, adjusted 30.3 -> PMI 95.7."""
    candidate = UserFactory()
    solution = _make_solution(candidate)
    _build_cat_assessment(solution, candidate, order=0, ranked=False)

    result = _compute_for_career(solution, candidate, CAREER, "IT Sector", "ITCP")
    cat = _assessment_result(result, "CAT")

    # mapping scores from the user-defined table: 5,5,5,5,5,4 = 29 (SRS §5.1.1)
    assert sorted(v.mapping_score for v in cat.variables) == [4, 5, 5, 5, 5, 5]
    assert cat.sum_product == 29
    assert cat.max_product == 30  # 6 variables x MAX(table)=5
    assert cat.max_product + cat.max_product / 100 == pytest.approx(30.3)
    assert cat.pmi == pytest.approx(95.7, abs=0.05)


def test_standard_with_rank_pmi_oracle():
    """SRS §5.1.2: summary 43, max 45, adjusted 45.45 -> PMI 94.6."""
    candidate = UserFactory()
    solution = _make_solution(candidate)
    _build_cat_assessment(solution, candidate, order=0, ranked=True)

    result = _compute_for_career(solution, candidate, CAREER, "IT Sector", "ITCP")
    cat = _assessment_result(result, "CAT")

    assert all(v.mode == "standard_ranked" for v in cat.variables)
    # product scores 7,9,6,8,5,8 = 43 (SRS §5.1.1 with-rank table)
    assert sorted(v.product_score for v in cat.variables) == [5, 6, 7, 8, 8, 9]
    assert cat.sum_product == 43
    assert cat.max_product == 45  # sum(MAX(table)=5 x rank_value) = 5 x 9
    assert cat.max_product + cat.max_product / 100 == pytest.approx(45.45)
    assert cat.pmi == pytest.approx(94.6, abs=0.05)


# ---------------------------------------------------------------------------
# Polar PMI oracle (SRS §5.2.2)
# ---------------------------------------------------------------------------


def test_polar_pmi_oracle():
    """SRS §5.2.2: summary 144, max 145, adjusted 146.45 -> PMI 98.33.

    The max mapping score uses the HM rank value at each variable's rank_order
    (H3) — NOT the actual match code's rank value. The Enterprising-Aesthetic
    variable is an MM match at Rank6: its product uses MM@6 (=3) but its max
    contribution uses HM@6 (=2), which is what distinguishes the corrected
    denominator (145) from the naive one.
    """
    candidate = UserFactory()
    solution = _make_solution(candidate)
    _build_cia_assessment(solution, candidate, order=0)

    result = _compute_for_career(solution, candidate, CAREER, "IT Sector", "ITCP")
    cia = _assessment_result(result, "CIA")

    assert all(v.mode == "polar" for v in cia.variables)
    # product scores 17,23,28,35,9,32 = 144 (SRS §5.2.1)
    assert sorted(v.product_score for v in cia.variables) == [9, 17, 23, 28, 32, 35]
    assert cia.sum_product == 144
    assert cia.max_product == 145  # (5x7)+(5x6.4)+(5x5.6)+(5x4.6)+(5x3.4)+(5x2)
    assert cia.max_product + cia.max_product / 100 == pytest.approx(146.45)
    assert cia.pmi == pytest.approx(98.33, abs=0.05)

    # The Enterprising-Aesthetic variable proves the HM-based max: actual weight
    # is MM@6=3 (used in product/VMI) but max_weight is HM@6=2 (used in max).
    ea = next(v for v in cia.variables if v.variable == "Enterprising-Aesthetic")
    assert ea.weight == 3.0
    assert ea.max_weight == 2.0
    assert ea.vmi == 60.0  # 9 / (5 x 3) x 100


# ---------------------------------------------------------------------------
# FMI oracles (SRS §5.3)
# ---------------------------------------------------------------------------


def test_fmi_without_rank_oracle():
    """SRS §5.3: FMI = (95.7 + 98.33) / 2 = 97.01 (CAT unranked + CIA polar)."""
    candidate = UserFactory()
    solution = _make_solution(candidate)
    _build_cat_assessment(solution, candidate, order=0, ranked=False)
    _build_cia_assessment(solution, candidate, order=1)

    mi = compute_match_indices(solution, candidate)
    assert len(mi) == 1
    assert mi[0].career_title == CAREER
    assert mi[0].final_match_index == pytest.approx(97.01, abs=0.05)


def test_fmi_with_rank_oracle():
    """SRS §5.3: FMI = (94.6 + 98.33) / 2 = 96.46 (CAT ranked + CIA polar)."""
    candidate = UserFactory()
    solution = _make_solution(candidate)
    _build_cat_assessment(solution, candidate, order=0, ranked=True)
    _build_cia_assessment(solution, candidate, order=1)

    mi = compute_match_indices(solution, candidate)
    assert len(mi) == 1
    assert mi[0].final_match_index == pytest.approx(96.46, abs=0.05)
