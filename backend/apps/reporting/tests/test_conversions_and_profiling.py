"""Tests for the reporting correctness fixes H4/H5/H6.

Covers:
  - H4: real norm-based statistical conversions (STEN/STENINE/percentile) and
        that the selected stat_conversion drives cutoff/band thresholds.
  - H5: the PMI report (per-assessment) + PMI-D gap index (may be negative,
        ordered by gap descending) — SRS 06 §3.3.
  - H6: ReportBand.target_type resolving a band against FMI/PMI values in a
        profiling report — SRS 06 §3.1-3.4.

Hand-computed norm (population = section-score percentages):
  population [30, 70] -> mean 50, population SD 20.
  z = (value - 50) / 20.
  STEN    = round(5.5 + 2z) clamped 1..10 ; STENINE = round(5 + 2z) clamped 1..9.
    value 70 -> z=1.0  -> STEN 8,  STENINE 7
    value 90 -> z=2.0  -> STEN 10, STENINE 9
    value 10 -> z=-2.0 -> STEN 2,  STENINE 1
  percentile (mid-rank) of value in [30, 70]:
    30 -> 25.0 ; 50 -> 50.0 ; 70 -> 75.0
(All rounding is Python round()/banker's rounding; the values above are the
actual outputs — see the inline verification in the test.)
"""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import (
    Assessment,
    AssessmentSection,
    AssessmentSession,
    SectionScore,
)
from apps.assessment.tests.factories import get_or_create_role
from apps.career_profiling.models import MatchIndex, ProfilingSolution
from apps.reporting.generation import (
    _build_descriptive,
    _build_interpretative,
    _build_profiling,
    _compute_norm,
    _convert_score,
    _NormContext,
    _percentile_rank,
)
from apps.reporting.models import Report, ReportBand, ReportCutoff

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    from apps.accounts.services import get_or_create_default_roles

    return get_or_create_default_roles()


def _make_user(email):
    return UserFactory.create(role=get_or_create_role("individual", is_system=True), email=email)


# ---------------------------------------------------------------------------
# H4 — statistical conversions (pure function, hand-computed integers)
# ---------------------------------------------------------------------------


def test_norm_context_mean_and_sd():
    """Population [30, 70] -> mean 50, population SD 20."""
    norm = _NormContext([30.0, 70.0])
    assert norm.mean == 50.0
    assert norm.sd == 20.0
    assert norm.fell_back is False


def test_sten_conversion_hand_computed():
    """STEN = round(5.5 + 2z) clamped 1..10, integer."""
    norm = _NormContext([30.0, 70.0])  # mean 50, sd 20
    assert _convert_score(70.0, "sten", norm) == 8  # z=1.0 -> round(7.5)=8
    assert _convert_score(90.0, "sten", norm) == 10  # z=2.0 -> round(9.5)=10 (clamp ok)
    assert _convert_score(10.0, "sten", norm) == 2  # z=-2.0 -> round(1.5)=2
    # Clamping to the 1..10 range
    assert _convert_score(1000.0, "sten", norm) == 10
    assert _convert_score(-1000.0, "sten", norm) == 1
    # Results are integers, not floats
    assert isinstance(_convert_score(70.0, "sten", norm), int)


def test_stenine_conversion_hand_computed():
    """STENINE = round(5 + 2z) clamped 1..9, integer."""
    norm = _NormContext([30.0, 70.0])  # mean 50, sd 20
    assert _convert_score(70.0, "stenine", norm) == 7  # z=1.0 -> round(7)=7
    assert _convert_score(90.0, "stenine", norm) == 9  # z=2.0 -> round(9)=9
    assert _convert_score(10.0, "stenine", norm) == 1  # z=-2.0 -> round(1)=1
    assert _convert_score(1000.0, "stenine", norm) == 9
    assert isinstance(_convert_score(70.0, "stenine", norm), int)


def test_percentile_rank_hand_computed():
    """Percentile mid-rank of a value within the population [30, 70]."""
    norm = _NormContext([30.0, 70.0])
    assert _convert_score(30.0, "percentile", norm) == 25.0
    assert _convert_score(50.0, "percentile", norm) == 50.0
    assert _convert_score(70.0, "percentile", norm) == 75.0
    assert _percentile_rank(70.0, [30.0, 70.0]) == 75.0


def test_conversion_graceful_fallback_when_sd_zero():
    """Degenerate population (SD 0): STEN/STENINE fall back to mid-scale."""
    norm = _NormContext([50.0])  # single value -> sd 0
    assert norm.sd == 0.0
    assert norm.fell_back is True
    assert _convert_score(80.0, "sten", norm) == 6  # z forced 0 -> round(5.5)=6
    assert _convert_score(80.0, "stenine", norm) == 5  # z forced 0 -> round(5)=5
    # Percentile with empty population falls back to the percentage
    assert _convert_score(80.0, "percentile", _NormContext([])) == 80.0
    assert _compute_norm([]) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# H4 — the selected stat_conversion DRIVES cutoff / band thresholds
# ---------------------------------------------------------------------------


def _make_session_two_sections(roles):
    """A completed session with section A=70% and section B=30%.

    Norm population (all section percentages) = [70, 30] -> mean 50, sd 20.
    """
    assessment = Assessment.objects.create(title="A", status="published")
    candidate = _make_user("h4cand@test.com")
    session = AssessmentSession.objects.create(
        assessment=assessment,
        candidate=candidate,
        status="completed",
        total_score=100.0,
        max_score=200.0,
        percentage=50.0,
    )
    sec_a = AssessmentSection.objects.create(assessment=assessment, title="A", level=1, order=1)
    sec_b = AssessmentSection.objects.create(assessment=assessment, title="B", level=1, order=2)
    SectionScore.objects.create(session=session, section=sec_a, raw_score=70.0, max_score=100.0)
    SectionScore.objects.create(session=session, section=sec_b, raw_score=30.0, max_score=100.0)
    return assessment, candidate, session, sec_a, sec_b


def test_stat_conversion_drives_cutoff(roles):
    """Same cutoff (60) on a 70% section: above under 'percentage', below under
    'sten' (STEN value 8 < 60)."""
    assessment, candidate, session, sec_a, _ = _make_session_two_sections(roles)
    report = Report.objects.create(
        title="Desc",
        report_type="descriptive",
        scope="general",
        assessment=assessment,
        status="published",
        stat_conversion="percentage",
    )
    ReportCutoff.objects.create(
        report=report,
        section=sec_a,
        cutoff_score=60.0,
        cutoff_label="Avg",
        above_description="ABOVE",
        below_description="BELOW",
    )

    d_pct = _build_descriptive(report, session)["cutoffs"][0]
    assert d_pct["candidate_score"] == 70.0
    assert d_pct["is_above_cutoff"] is True
    assert d_pct["description"] == "ABOVE"

    report.stat_conversion = "sten"
    report.save(update_fields=["stat_conversion"])
    d_sten = _build_descriptive(report, session)["cutoffs"][0]
    assert d_sten["candidate_score"] == 8  # z=1.0 -> STEN 8
    assert d_sten["is_above_cutoff"] is False  # 8 < 60
    assert d_sten["description"] == "BELOW"


def test_stat_conversion_drives_band_membership(roles):
    """A STEN band [6, 10] on a 70% section: matches only under 'sten'
    (value 8), not under 'percentage' (value 70 out of [6, 10])."""
    assessment, candidate, session, sec_a, _ = _make_session_two_sections(roles)
    report = Report.objects.create(
        title="Interp",
        report_type="interpretative",
        scope="general",
        assessment=assessment,
        status="published",
        stat_conversion="percentage",
    )
    ReportBand.objects.create(
        report=report,
        section=sec_a,
        target_type="section",
        band_number=1,
        range_min=6,
        range_max=10,
        band_label="High STEN",
    )

    bands_pct = _build_interpretative(report, session)["bands"]
    assert bands_pct == []  # 70 not in [6, 10]

    report.stat_conversion = "sten"
    report.save(update_fields=["stat_conversion"])
    bands_sten = _build_interpretative(report, session)["bands"]
    assert len(bands_sten) == 1
    assert bands_sten[0]["candidate_score"] == 8
    assert bands_sten[0]["band_label"] == "High STEN"


# ---------------------------------------------------------------------------
# H5 — PMI report + PMI-D gap index
# ---------------------------------------------------------------------------


def _profiling_setup(candidate_email):
    solution = ProfilingSolution.objects.create(title="S", status="published")
    candidate = _make_user(candidate_email)
    assessment = Assessment.objects.create(title="Host", status="published")
    session = AssessmentSession.objects.create(
        assessment=assessment,
        candidate=candidate,
        status="completed",
        total_score=7.0,
        max_score=10.0,
        percentage=70.0,
    )
    return solution, candidate, session


def _mi(solution, candidate, stream, title, code, cat_pmi, cia_pmi, fmi):
    """A MatchIndex whose variable_details carry per-assessment PMI for CAT/CIA."""
    return MatchIndex.objects.create(
        solution=solution,
        candidate=candidate,
        career_stream=stream,
        career_title=title,
        career_code=code,
        final_match_index=fmi,
        variable_mapping_index=fmi,
        variable_details=[
            {"variable": "v1", "assessment": "CAT", "pmi": cat_pmi, "vmi": 80.0},
            {"variable": "v2", "assessment": "CIA", "pmi": cia_pmi, "vmi": 60.0},
        ],
    )


def test_pmi_d_produces_negative_gap_and_orders_descending(roles):
    """PMI-D = CAT-PMI - CIA-PMI. Career X (75.2 - 98.5 = -23.3) is negative;
    Career Y (90 - 50 = 40) positive. Ordered by gap descending: Y then X."""
    solution, candidate, session = _profiling_setup("pmid@test.com")
    _mi(solution, candidate, "IT", "CareerX", "X", cat_pmi=75.2, cia_pmi=98.5, fmi=80.0)
    _mi(solution, candidate, "Med", "CareerY", "Y", cat_pmi=90.0, cia_pmi=50.0, fmi=85.0)

    report = Report.objects.create(
        title="Prof",
        report_type="descriptive",
        scope="profiling",
        profiling_solution=solution,
        status="published",
        include_raw_summary=False,
        include_pmi=True,
        pmi_d_first_assessment="CAT",
        pmi_d_second_assessment="CIA",
    )
    pmi = _build_profiling(report, session)["pmi"]

    # Per-assessment PMI listed for both assessments
    assert set(pmi["assessments"]) == {"CAT", "CIA"}
    assert "CAT" in pmi["by_assessment"] and "CIA" in pmi["by_assessment"]

    gap = pmi["gap_index"]
    assert gap["first_assessment"] == "CAT"
    assert gap["second_assessment"] == "CIA"
    careers = gap["careers"]
    assert [c["career_title"] for c in careers] == ["CareerY", "CareerX"]  # 40 then -23.3
    assert careers[0]["pmi_d"] == 40.0
    assert careers[1]["pmi_d"] == -23.3  # negative gap produced
    # Ordered descending
    assert careers[0]["pmi_d"] > careers[1]["pmi_d"]


def test_pmi_d_bands_apply_to_negative_gap(roles):
    """A pmi_d band with a negative range (-25 to -5) labels the -23.3 gap."""
    solution, candidate, session = _profiling_setup("pmidband@test.com")
    _mi(solution, candidate, "IT", "CareerX", "X", cat_pmi=75.2, cia_pmi=98.5, fmi=80.0)

    report = Report.objects.create(
        title="Prof",
        report_type="descriptive",
        scope="profiling",
        profiling_solution=solution,
        status="published",
        include_raw_summary=False,
        include_pmi=True,
        pmi_d_first_assessment="CAT",
        pmi_d_second_assessment="CIA",
    )
    ReportBand.objects.create(
        report=report,
        section=None,
        target_type="pmi_d",
        band_number=5,
        range_min=-25,
        range_max=-5,
        band_label="Moderate Gap",
        colour_code="Yellow",
    )
    gap = _build_profiling(report, session)["pmi"]["gap_index"]
    assert gap["careers"][0]["band"]["band_label"] == "Moderate Gap"


# ---------------------------------------------------------------------------
# H6 — target_type bands against FMI / PMI
# ---------------------------------------------------------------------------


def test_fmi_target_band_resolves_against_fmi(roles):
    """A target_type='fmi' band [75, 100] labels the FMI-88.5 career but not
    the FMI-45 career."""
    solution, candidate, session = _profiling_setup("fmiband@test.com")
    _mi(solution, candidate, "IT", "HighCareer", "H", cat_pmi=80, cia_pmi=80, fmi=88.5)
    _mi(solution, candidate, "IT", "LowCareer", "L", cat_pmi=40, cia_pmi=40, fmi=45.0)

    report = Report.objects.create(
        title="Prof",
        report_type="descriptive",
        scope="profiling",
        profiling_solution=solution,
        status="published",
        include_raw_summary=False,
        include_fmi=True,
    )
    ReportBand.objects.create(
        report=report,
        section=None,
        target_type="fmi",
        band_number=1,
        range_min=75,
        range_max=100,
        band_label="Great match",
    )
    fmi = _build_profiling(report, session)["fmi"]
    by_title = {f["career_title"]: f for f in fmi}
    assert by_title["HighCareer"]["band"]["band_label"] == "Great match"
    assert by_title["LowCareer"]["band"] is None


def test_pmi_target_band_scoped_by_assessment(roles):
    """A target_type='pmi' band scoped to assessment_label='CAT' [70, 100]
    labels the CAT PMI (75.2) but is not applied to the CIA PMI list."""
    solution, candidate, session = _profiling_setup("pmiband2@test.com")
    _mi(solution, candidate, "IT", "CareerX", "X", cat_pmi=75.2, cia_pmi=40.0, fmi=80.0)

    report = Report.objects.create(
        title="Prof",
        report_type="descriptive",
        scope="profiling",
        profiling_solution=solution,
        status="published",
        include_raw_summary=False,
        include_pmi=True,
    )
    ReportBand.objects.create(
        report=report,
        section=None,
        target_type="pmi",
        assessment_label="CAT",
        band_number=1,
        range_min=70,
        range_max=100,
        band_label="Strong",
    )
    pmi = _build_profiling(report, session)["pmi"]
    cat_entry = pmi["by_assessment"]["CAT"][0]
    cia_entry = pmi["by_assessment"]["CIA"][0]
    assert cat_entry["band"]["band_label"] == "Strong"
    # The CAT-scoped band must NOT label the CIA PMI list.
    assert cia_entry["band"] is None
