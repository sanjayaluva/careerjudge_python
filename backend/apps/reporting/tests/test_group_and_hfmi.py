"""Tests for the Reporting module's group report + HFMI/LFMI selection.

Covers:
  - Group report aggregation across multiple sessions (SRS 04 group report)
  - HFMI / LFMI data selection for profiling reports (SRS 06 SRS 2.2)

Auth setup: psychometrician role with full reporting rights.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import (
    Assessment,
    AssessmentSection,
    AssessmentSession,
    SectionScore,
)
from apps.assessment.tests.factories import get_or_create_role
from apps.career_profiling.models import (
    MatchIndex,
    ProfilingSolution,
)
from apps.reporting.generation import generate_group_report_data, select_profiling_data
from apps.reporting.models import Report

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def roles(db):
    """Pre-create the default roles so UserFactory can assign 'individual'."""
    return get_or_create_default_roles()


@pytest.fixture
def psychometrician_user(db, roles):
    role = roles["psychometrician"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="reporting", action=action)
        ModuleRight.objects.get_or_create(role=role, module="career_profiling", action=action)
    return UserFactory(role=role, email="psy@test.com")


@pytest.fixture
def psy_client(db, psychometrician_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(psychometrician_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(email):
    """Create a user with the 'individual' role (idempotent — get_or_create)."""
    return UserFactory.create(role=get_or_create_role("individual", is_system=True), email=email)


def _make_completed_session(assessment, candidate, percentage):
    """Create a completed session with a single SectionScore at the given %."""
    session = AssessmentSession.objects.create(
        assessment=assessment,
        candidate=candidate,
        status="completed",
        total_score=float(percentage),
        max_score=100.0,
        percentage=float(percentage),
    )
    section = AssessmentSection.objects.create(
        assessment=assessment, title=f"V{candidate.id}", level=1, order=1
    )
    SectionScore.objects.create(
        session=session, section=section, raw_score=float(percentage), max_score=100.0
    )
    return session, section


def _make_match_index(solution, candidate, career_stream, career_title, career_code, fmi):
    """Create a MatchIndex row with the given FMI."""
    return MatchIndex.objects.create(
        solution=solution,
        candidate=candidate,
        career_stream=career_stream,
        career_title=career_title,
        career_code=career_code,
        final_match_index=fmi,
        variable_mapping_index=fmi,
        variable_details=[],
    )


# ---------------------------------------------------------------------------
# Group report aggregation (unit tests on generate_group_report_data)
# ---------------------------------------------------------------------------


def test_group_report_aggregates_multiple_sessions(roles):
    """Group report with 3 sessions at 30%, 70%, 90%:
    - candidate_count = 3
    - average_percentage = (30 + 70 + 90) / 3 = 63.33
    - min = 30, max = 90
    - pass_threshold = 40 -> 2 of 3 pass -> pass_rate = 66.67
    - distribution: 1 fail, 0 below_avg, 1 average, 1 above_avg
    """
    assessment = Assessment.objects.create(title="A", status="published")
    c1 = _make_user("c1@test.com")
    c2 = _make_user("c2@test.com")
    c3 = _make_user("c3@test.com")
    s1, _ = _make_completed_session(assessment, c1, 30.0)
    s2, _ = _make_completed_session(assessment, c2, 70.0)
    s3, _ = _make_completed_session(assessment, c3, 90.0)

    report = Report.objects.create(
        title="Group Report",
        report_type="group",
        scope="general",
        assessment=assessment,
        status="published",
    )
    result = generate_group_report_data(report, [s1, s2, s3])

    assert result["candidate_count"] == 3
    assert result["average_percentage"] == pytest.approx(63.33, abs=0.1)
    assert result["min_percentage"] == 30.0
    assert result["max_percentage"] == 90.0
    assert result["pass_count"] == 2
    assert result["pass_rate"] == pytest.approx(66.67, abs=0.1)
    assert result["distribution"]["fail (0-40)"] == 1
    assert result["distribution"]["average (60-80)"] == 1
    assert result["distribution"]["above_avg (80-100)"] == 1
    assert len(result["candidates"]) == 3


def test_group_report_empty_sessions_returns_placeholder(roles):
    """Empty session list returns a placeholder response, not an error."""
    report = Report.objects.create(title="Empty", report_type="group", status="published")
    result = generate_group_report_data(report, [])
    assert result["candidate_count"] == 0
    assert "note" in result


def test_group_report_section_averages(roles):
    """Group report computes per-section mean across the group."""
    assessment = Assessment.objects.create(title="A", status="published")
    section = AssessmentSection.objects.create(assessment=assessment, title="V1", level=1, order=1)

    candidates = [_make_user(f"c{i}@test.com") for i in range(3)]
    sessions = []
    for i, c in enumerate(candidates, start=1):
        session = AssessmentSession.objects.create(
            assessment=assessment,
            candidate=c,
            status="completed",
            total_score=float(i * 20),
            max_score=100.0,
            percentage=float(i * 20),
        )
        SectionScore.objects.create(
            session=session, section=section, raw_score=float(i * 20), max_score=100.0
        )
        sessions.append(session)

    report = Report.objects.create(
        title="G", report_type="group", assessment=assessment, status="published"
    )
    result = generate_group_report_data(report, sessions)
    sa = result["section_averages"][0]
    assert sa["section_title"] == "V1"
    # 20, 40, 60 -> mean 40
    assert sa["average_percentage"] == 40.0
    assert sa["min_percentage"] == 20.0
    assert sa["max_percentage"] == 60.0
    assert sa["candidate_count"] == 3


# ---------------------------------------------------------------------------
# Group report API endpoint
# ---------------------------------------------------------------------------


def test_generate_group_endpoint_returns_aggregated_data(psy_client, psychometrician_user):
    """POST /api/reporting/reports/<id>/generate-group/ returns the group report."""
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Group",
        report_type="group",
        scope="general",
        assessment=assessment,
        status="published",
        created_by=psychometrician_user,
    )
    c1 = _make_user("c1@test.com")
    c2 = _make_user("c2@test.com")
    s1, _ = _make_completed_session(assessment, c1, 60.0)
    s2, _ = _make_completed_session(assessment, c2, 80.0)

    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/generate_group/",
        {"session_ids": [s1.id, s2.id]},
        format="json",
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    data = resp.data["data"]
    assert data["candidate_count"] == 2
    assert data["average_percentage"] == 70.0
    assert data["pass_count"] == 2


def test_generate_group_rejects_non_group_report(psy_client, psychometrician_user):
    """generate_group is only valid for report_type='group'."""
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Descriptive",
        report_type="descriptive",
        scope="general",
        assessment=assessment,
        status="published",
        created_by=psychometrician_user,
    )
    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/generate_group/",
        {"session_ids": [1]},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["error"]["code"] == "validation_error"


def test_generate_group_rejects_draft_report(psy_client, psychometrician_user):
    """Report must be published before generating a group report."""
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Group",
        report_type="group",
        scope="general",
        assessment=assessment,
        status="draft",
        created_by=psychometrician_user,
    )
    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/generate_group/",
        {"session_ids": [1]},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "forbidden"


def test_generate_group_rejects_missing_session_ids(psy_client, psychometrician_user):
    """session_ids is required."""
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Group",
        report_type="group",
        scope="general",
        assessment=assessment,
        status="published",
        created_by=psychometrician_user,
    )
    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/generate_group/",
        {},
        format="json",
    )
    assert resp.status_code == 400
    assert "session_ids" in resp.data["error"]["message"]


# ---------------------------------------------------------------------------
# HFMI / LFMI data selection (unit tests on select_profiling_data)
# ---------------------------------------------------------------------------


def test_hfmi_system_mode_returns_top_n_careers(roles):
    """System-initiated HFMI: returns the careers with the highest FMIs,
    grouped by stream. With n_categories=1, n_criterions=2, returns the top
    stream's top 2 careers."""
    solution = ProfilingSolution.objects.create(title="S", status="published")
    candidate = _make_user("candidate1@test.com")
    # 5 careers across 2 streams
    _make_match_index(solution, candidate, "IT", "Prog", "ITP", 95.0)
    _make_match_index(solution, candidate, "IT", "Analyst", "ITA", 90.0)
    _make_match_index(solution, candidate, "IT", "Admin", "ITAD", 80.0)
    _make_match_index(solution, candidate, "Finance", "Accountant", "FA", 88.0)
    _make_match_index(solution, candidate, "Finance", "Auditor", "FAU", 70.0)

    indices = list(MatchIndex.objects.filter(solution=solution))
    result = select_profiling_data(
        indices,
        data_type="HFMI",
        extraction_mode="system",
        n_categories=1,
        n_criterions=2,
    )
    assert result["selected_count"] == 2
    titles = [c["career_title"] for c in result["selected"]]
    # IT stream has the highest FMI (95), so top 2 IT careers are returned
    assert "Prog" in titles
    assert "Analyst" in titles
    assert "Accountant" not in titles


def test_lfmi_system_mode_returns_bottom_n_careers(roles):
    """System-initiated LFMI: returns the careers with the LOWEST FMIs."""
    solution = ProfilingSolution.objects.create(title="S", status="published")
    candidate = _make_user("candidate2@test.com")
    _make_match_index(solution, candidate, "IT", "Prog", "ITP", 95.0)
    _make_match_index(solution, candidate, "Finance", "Auditor", "FAU", 30.0)
    _make_match_index(solution, candidate, "Finance", "Accountant", "FA", 40.0)

    indices = list(MatchIndex.objects.filter(solution=solution))
    result = select_profiling_data(
        indices,
        data_type="LFMI",
        extraction_mode="system",
        n_categories=1,
        n_criterions=2,
    )
    # LFMI: Finance stream has the lowest FMI (30), top 2 finance careers
    titles = [c["career_title"] for c in result["selected"]]
    assert "Auditor" in titles
    assert "Accountant" in titles
    assert "Prog" not in titles


def test_hfmi_user_mode_with_fmi_range_filters(roles):
    """User-initiated HFMI: filter by FMI range, return all matching."""
    solution = ProfilingSolution.objects.create(title="S", status="published")
    candidate = _make_user("candidate3@test.com")
    _make_match_index(solution, candidate, "IT", "Prog", "ITP", 95.0)
    _make_match_index(solution, candidate, "IT", "Analyst", "ITA", 88.0)
    _make_match_index(solution, candidate, "IT", "Admin", "ITAD", 60.0)

    indices = list(MatchIndex.objects.filter(solution=solution))
    result = select_profiling_data(
        indices,
        data_type="HFMI",
        extraction_mode="user",
        fmi_range=(85.0, 100.0),
    )
    # Only Prog (95) and Analyst (88) fall in [85, 100]
    titles = {c["career_title"] for c in result["selected"]}
    assert titles == {"Prog", "Analyst"}


def test_hfmi_user_mode_with_manual_selection(roles):
    """User-initiated HFMI: user manually selects careers from the filtered list."""
    solution = ProfilingSolution.objects.create(title="S", status="published")
    candidate = _make_user("candidate4@test.com")
    _make_match_index(solution, candidate, "IT", "Prog", "ITP", 95.0)
    _make_match_index(solution, candidate, "IT", "Analyst", "ITA", 88.0)
    _make_match_index(solution, candidate, "IT", "Admin", "ITAD", 60.0)

    indices = list(MatchIndex.objects.filter(solution=solution))
    result = select_profiling_data(
        indices,
        data_type="HFMI",
        extraction_mode="user",
        fmi_range=(50.0, 100.0),
        selected_career_titles=["Prog"],  # user picks only Prog
    )
    titles = [c["career_title"] for c in result["selected"]]
    assert titles == ["Prog"]


# ---------------------------------------------------------------------------
# HFMI/LFMI API endpoint
# ---------------------------------------------------------------------------


def test_select_data_endpoint_returns_filtered_careers(psy_client, psychometrician_user):
    """POST /api/reporting/reports/<id>/select_data/ returns HFMI/LFMI selection."""
    solution = ProfilingSolution.objects.create(
        title="S",
        status="published",
        created_by=psychometrician_user,
    )
    candidate = _make_user("candidate5@test.com")
    _make_match_index(solution, candidate, "IT", "Prog", "ITP", 95.0)
    _make_match_index(solution, candidate, "IT", "Analyst", "ITA", 88.0)
    _make_match_index(solution, candidate, "Finance", "Auditor", "FAU", 30.0)

    report = Report.objects.create(
        title="Profiling",
        report_type="descriptive",
        scope="profiling",
        profiling_solution=solution,
        status="published",
        created_by=psychometrician_user,
    )

    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/select_data/",
        {
            "candidate_id": candidate.id,
            "data_type": "HFMI",
            "extraction_mode": "system",
            "n_categories": 1,
            "n_criterions": 2,
        },
        format="json",
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    data = resp.data["data"]
    assert data["data_type"] == "HFMI"
    assert data["extraction_mode"] == "system"
    titles = [c["career_title"] for c in data["selected"]]
    assert "Prog" in titles  # FMI 95
    assert "Auditor" not in titles  # FMI 30 — too low for HFMI


def test_select_data_rejects_general_report(psy_client, psychometrician_user):
    """select_data is only for profiling reports."""
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Gen",
        report_type="descriptive",
        scope="general",
        assessment=assessment,
        status="published",
        created_by=psychometrician_user,
    )
    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/select_data/",
        {"candidate_id": 1, "data_type": "HFMI", "extraction_mode": "system"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Band endpoint (REP-3): profiling target-type bands via POST
# ---------------------------------------------------------------------------


def test_create_profiling_band_without_section(psy_client, psychometrician_user):
    """REP-3: POST /reports/<id>/bands/ accepts an FMI band with no `section`.

    The frontend Bands tab now offers FMI/PMI/VMI/raw_summary/PMI-D targets
    (SRS 06 §3.1-3.4); those bands carry no assessment section, so the endpoint
    must accept a payload where `section` is omitted.
    """
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Prof",
        report_type="interpretative",
        scope="profiling",
        assessment=assessment,
        status="draft",
        include_fmi=True,
        created_by=psychometrician_user,
    )
    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/bands/",
        {
            "target_type": "fmi",
            "band_number": 1,
            "range_min": 75,
            "range_max": 100,
            "band_label": "Strong match",
        },
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["target_type"] == "fmi"
    assert resp.data["data"]["section"] is None


def test_create_pmi_band_scoped_by_assessment_label(psy_client, psychometrician_user):
    """REP-3: a PMI band may be scoped to a single assessment via assessment_label."""
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Prof",
        report_type="interpretative",
        scope="profiling",
        assessment=assessment,
        status="draft",
        include_pmi=True,
        created_by=psychometrician_user,
    )
    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/bands/",
        {
            "target_type": "pmi",
            "assessment_label": "CAT",
            "band_number": 1,
            "range_min": 70,
            "range_max": 100,
            "band_label": "High CAT PMI",
        },
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["assessment_label"] == "CAT"


def test_create_section_band_without_section_is_rejected(psy_client, psychometrician_user):
    """A section-target band still requires `section` (serializer validation)."""
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Interp",
        report_type="interpretative",
        scope="general",
        assessment=assessment,
        status="draft",
        created_by=psychometrician_user,
    )
    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/bands/",
        {"target_type": "section", "band_number": 1, "range_min": 0, "range_max": 50},
        format="json",
    )
    assert resp.status_code == 400, f"Got {resp.status_code}: {resp.data}"


# ---------------------------------------------------------------------------
# Report duplication / templates (REP-2)
# ---------------------------------------------------------------------------


def test_duplicate_report_clones_config(psy_client, psychometrician_user):
    """REP-2: POST /reports/<id>/duplicate/ clones config into a new draft."""
    from apps.assessment.models import AssessmentSection
    from apps.reporting.models import ReportBand, ReportSection

    assessment = Assessment.objects.create(title="A", status="published")
    section = AssessmentSection.objects.create(
        assessment=assessment, title="Verbal", level=1, order=1
    )
    report = Report.objects.create(
        title="Master",
        report_type="interpretative",
        scope="general",
        assessment=assessment,
        status="published",
        include_fmi=True,
        created_by=psychometrician_user,
    )
    ReportSection.objects.create(
        report=report,
        section_type="custom",
        title="Intro",
        order=1,
        table_graph_config={"layout": "graph"},
    )
    ReportBand.objects.create(
        report=report,
        target_type="section",
        section=section,
        band_number=1,
        range_min=0,
        range_max=50,
        band_label="Low",
    )

    resp = psy_client.post(f"/api/reporting/reports/{report.id}/duplicate/", {}, format="json")
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    new_id = resp.data["data"]["id"]
    assert new_id != report.id
    assert resp.data["data"]["title"] == "Master (copy)"
    assert resp.data["data"]["status"] == "draft"
    assert resp.data["data"]["include_fmi"] is True

    clone = Report.objects.get(pk=new_id)
    assert clone.sections.count() == 1
    assert clone.sections.first().table_graph_config == {"layout": "graph"}
    assert clone.bands.count() == 1
    assert clone.bands.first().band_label == "Low"
    # Source is untouched.
    assert report.sections.count() == 1
    assert report.bands.count() == 1


def test_duplicate_report_accepts_custom_title(psy_client, psychometrician_user):
    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Master",
        report_type="descriptive",
        scope="general",
        assessment=assessment,
        status="draft",
        created_by=psychometrician_user,
    )
    resp = psy_client.post(
        f"/api/reporting/reports/{report.id}/duplicate/",
        {"title": "2026 Intake Template"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["title"] == "2026 Intake Template"
