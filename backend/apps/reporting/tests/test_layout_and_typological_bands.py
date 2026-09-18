"""Tests for the dossier "medium" reporting gaps (D4):

  - Typological band definitions: top-N type-profile variables are banded
    against the report's target_type='section' ReportBand rows (SRS §3.2.1),
    reusing the ReportBand + target_type machinery from H6.
  - Report-section description + uploaded image surface in generation and
    the PDF (SRS §2.1.2).
  - Table layout: table_graph_config with layout='table' computes an
    end-to-end table of section scores (data -> PDF table), per
    SRS §3.1.2/§3.2.2/§3.3.2. Graph layout is recorded but scoped out.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import Assessment, AssessmentSection, AssessmentSession, SectionScore
from apps.assessment.tests.factories import get_or_create_role
from apps.reporting.generation import _build_typological, generate_report_data
from apps.reporting.models import Report, ReportBand, ReportSection, TypologicalCode
from apps.reporting.pdf import render_report_pdf

pytestmark = pytest.mark.django_db


def _make_user(email):
    return UserFactory.create(role=get_or_create_role("individual", is_system=True), email=email)


def _make_session_two_sections():
    """A completed session with section A=90% and section B=40%."""
    assessment = Assessment.objects.create(title="A", status="published")
    candidate = _make_user("layout@test.com")
    session = AssessmentSession.objects.create(
        assessment=assessment,
        candidate=candidate,
        status="completed",
        total_score=130.0,
        max_score=200.0,
        percentage=65.0,
    )
    sec_a = AssessmentSection.objects.create(
        assessment=assessment, title="Verbal", level=1, order=1
    )
    sec_b = AssessmentSection.objects.create(
        assessment=assessment, title="Numerical", level=1, order=2
    )
    SectionScore.objects.create(session=session, section=sec_a, raw_score=90.0, max_score=100.0)
    SectionScore.objects.create(session=session, section=sec_b, raw_score=40.0, max_score=100.0)
    return assessment, candidate, session, sec_a, sec_b


# ---------------------------------------------------------------------------
# Typological band definitions (SRS §3.2.1)
# ---------------------------------------------------------------------------


def test_typological_top_variable_carries_matching_band():
    """The top-scoring (90%) variable is labelled by its section band; the
    non-top (40%) variable isn't part of the type profile at all."""
    _assessment, _candidate, session, sec_a, sec_b = _make_session_two_sections()
    report = Report.objects.create(
        title="Type",
        report_type="typological",
        scope="general",
        assessment=_assessment,
        status="published",
    )
    TypologicalCode.objects.create(report=report, section=sec_a, code="V", top_n=1)
    TypologicalCode.objects.create(report=report, section=sec_b, code="N", top_n=1)
    ReportBand.objects.create(
        report=report,
        section=sec_a,
        target_type="section",
        band_number=1,
        range_min=80,
        range_max=100,
        band_label="Dominant",
        description="Strong verbal reasoning.",
    )

    result = _build_typological(report, session)
    assert result["type_profile"] == "V"
    top = result["top_variables"]
    assert len(top) == 1
    assert top[0]["variable"] == "Verbal"
    assert top[0]["band"]["band_label"] == "Dominant"
    assert top[0]["band"]["description"] == "Strong verbal reasoning."


def test_typological_variable_without_matching_band_has_none():
    _assessment, _candidate, session, sec_a, _sec_b = _make_session_two_sections()
    report = Report.objects.create(
        title="Type",
        report_type="typological",
        scope="general",
        assessment=_assessment,
        status="published",
    )
    TypologicalCode.objects.create(report=report, section=sec_a, code="V", top_n=1)
    # No bands defined at all.
    result = _build_typological(report, session)
    assert result["top_variables"][0]["band"] is None


def test_typological_report_with_bands_renders_pdf():
    """End-to-end: generate_report_data + render_report_pdf for a typological
    report whose top variable is banded."""
    _assessment, _candidate, session, sec_a, _sec_b = _make_session_two_sections()
    report = Report.objects.create(
        title="Type",
        report_type="typological",
        scope="general",
        assessment=_assessment,
        status="published",
    )
    TypologicalCode.objects.create(report=report, section=sec_a, code="V", top_n=1)
    ReportBand.objects.create(
        report=report,
        section=sec_a,
        target_type="section",
        band_number=1,
        range_min=80,
        range_max=100,
        band_label="Dominant",
        description="Strong verbal reasoning.",
    )
    rendered = generate_report_data(report, session)
    assert rendered["typological"]["top_variables"][0]["band"]["band_label"] == "Dominant"
    pdf = render_report_pdf(rendered)
    assert pdf.startswith(b"%PDF-")


# ---------------------------------------------------------------------------
# Section description + image upload (SRS §2.1.2)
# ---------------------------------------------------------------------------


def _tiny_png():
    # 1x1 transparent PNG.
    return SimpleUploadedFile(
        "pixel.png",
        (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
            b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00"
            b"\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        ),
        content_type="image/png",
    )


def test_section_description_and_image_surface_in_generation_and_pdf():
    _assessment, _candidate, session, _sec_a, _sec_b = _make_session_two_sections()
    report = Report.objects.create(
        title="Desc",
        report_type="descriptive",
        scope="general",
        assessment=_assessment,
        status="published",
    )
    ReportSection.objects.create(
        report=report,
        section_type="custom",
        title="About this report",
        description="This report was prepared by the psychometrics team.",
        image=_tiny_png(),
        order=0,
    )
    rendered = generate_report_data(report, session)
    section = rendered["sections"][0]
    assert section["description"] == "This report was prepared by the psychometrics team."
    assert section["image_url"]
    assert section["image_data_uri"].startswith("data:image/png;base64,")

    pdf = render_report_pdf(rendered)
    assert pdf.startswith(b"%PDF-")


def test_section_serializer_accepts_multipart_image_upload():
    """The `sections` create endpoint accepts a multipart image upload."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.accounts.models import ModuleRight
    from apps.accounts.services import get_or_create_default_roles

    roles = get_or_create_default_roles()
    role = roles["cj_admin"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="reporting", action=action)
    admin = UserFactory(role=role, email="repadmin@test.com")
    client = APIClient()
    refresh = RefreshToken.for_user(admin)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    assessment = Assessment.objects.create(title="A", status="published")
    report = Report.objects.create(
        title="Desc",
        report_type="descriptive",
        scope="general",
        assessment=assessment,
        status="draft",
        created_by=admin,
    )
    resp = client.post(
        f"/api/reporting/reports/{report.id}/sections/",
        {
            "section_type": "custom",
            "title": "Intro",
            "description": "Uploaded via multipart.",
            "image": _tiny_png(),
            "order": 0,
        },
        format="multipart",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    section = ReportSection.objects.get(id=resp.data["data"]["id"])
    assert section.description == "Uploaded via multipart."
    assert section.image.name


# ---------------------------------------------------------------------------
# Table/Graph layout (SRS §3.1.2/§3.2.2/§3.3.2)
# ---------------------------------------------------------------------------


def test_table_layout_builds_rows_from_section_scores_with_bands():
    _assessment, _candidate, session, sec_a, sec_b = _make_session_two_sections()
    report = Report.objects.create(
        title="Desc",
        report_type="descriptive",
        scope="general",
        assessment=_assessment,
        status="published",
        data_input_level="level1",
    )
    ReportBand.objects.create(
        report=report,
        section=sec_a,
        target_type="section",
        band_number=1,
        range_min=80,
        range_max=100,
        band_label="High",
        colour_code="#16a34a",
        description="Excellent.",
    )
    ReportSection.objects.create(
        report=report,
        section_type="chart",
        title="Score table",
        table_graph_config={
            "layout": "table",
            "table_title": "Your Intellectual Profile",
            "variable_label": "Aptitude",
            "score_label": "Your Score",
        },
        order=0,
    )
    rendered = generate_report_data(report, session)
    table = rendered["sections"][0]["table"]
    assert table["headers"]["table_title"] == "Your Intellectual Profile"
    assert table["headers"]["variable_label"] == "Aptitude"
    rows_by_variable = {r["variable"]: r for r in table["rows"]}
    assert rows_by_variable["Verbal"]["score"] == 90.0
    assert rows_by_variable["Verbal"]["label"] == "High"
    assert rows_by_variable["Verbal"]["colour_code"] == "#16a34a"
    assert rows_by_variable["Numerical"]["label"] == ""  # no band matches 40%

    pdf = render_report_pdf(rendered)
    assert pdf.startswith(b"%PDF-")


def test_graph_layout_renders_bar_chart(monkeypatch):
    """REP-1: layout='graph' now renders an SVG bar chart of section scores
    (previously scoped out)."""
    _assessment, _candidate, session, _sec_a, _sec_b = _make_session_two_sections()
    report = Report.objects.create(
        title="Desc",
        report_type="descriptive",
        scope="general",
        assessment=_assessment,
        status="published",
    )
    ReportSection.objects.create(
        report=report,
        section_type="chart",
        title="Score graph",
        table_graph_config={"layout": "graph"},
        order=0,
    )
    rendered = generate_report_data(report, session)
    entry = rendered["sections"][0]
    assert "table" not in entry
    assert "graph_note" not in entry
    graph = entry["graph"]
    assert len(graph["bars"]) == 2
    values = {b["variable"]: b["value"] for b in graph["bars"]}
    assert values["Verbal"] == 90.0
    assert values["Numerical"] == 40.0

    # The graph reaches the PDF HTML as inline SVG (no WeasyPrint needed).
    from apps.reporting.pdf import _build_custom_sections

    html = _build_custom_sections(
        [{"section_type": "chart", "title": "Score graph", "graph": graph, "is_visible": True}]
    )
    assert "<svg" in html and "Verbal" in html
