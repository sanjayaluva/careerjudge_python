"""M4 reporting: question-level breakdown (REP-6) and chart/graph rendering (REP-1).

  - REP-6: a report whose data_input_level='question' returns per-question
    rows (SRS 04 §2.3) instead of an empty section breakdown.
  - REP-1: a layout='graph' section renders an inline SVG bar chart instead of
    the old "scoped out" note (SRS 04 §2.2/§3.1.2, 06 §3.1.2).
"""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import (
    Assessment,
    AssessmentSection,
    AssessmentSession,
    QuestionAttempt,
    SectionScore,
)
from apps.assessment.tests.factories import get_or_create_role
from apps.question_bank.models import Question
from apps.reporting.generation import generate_report_data
from apps.reporting.models import Report, ReportSection

pytestmark = pytest.mark.django_db


def _make_user(email):
    return UserFactory.create(role=get_or_create_role("individual", is_system=True), email=email)


def _make_question(**overrides):
    defaults = {
        "question_type": "MCQ_TEXT_MULTI",
        "question_title": "T",
        "question_text_1": "Q?",
        "scoring_type": "ALL_OR_NOTHING",
        "status": "published",
    }
    defaults.update(overrides)
    return Question.objects.create(**defaults)


def _session_with_attempts():
    assessment = Assessment.objects.create(title="A", status="published")
    candidate = _make_user("qlevel@test.com")
    session = AssessmentSession.objects.create(
        assessment=assessment,
        candidate=candidate,
        status="completed",
        total_score=15.0,
        max_score=20.0,
        percentage=75.0,
    )
    section = AssessmentSection.objects.create(
        assessment=assessment, title="Verbal", level=1, order=1
    )
    SectionScore.objects.create(session=session, section=section, raw_score=15.0, max_score=20.0)
    q1 = _make_question(question_title="Capital of France", question_id_label="Q1")
    q2 = _make_question(question_title="2 + 2", question_id_label="Q2")
    QuestionAttempt.objects.create(
        session=session,
        question=q1,
        section=section,
        status="attempted",
        score=10.0,
        max_score=10.0,
    )
    QuestionAttempt.objects.create(
        session=session,
        question=q2,
        section=section,
        status="attempted",
        score=5.0,
        max_score=10.0,
    )
    return assessment, candidate, session, section


# ---------------------------------------------------------------------------
# REP-6 — question-level breakdown returns data
# ---------------------------------------------------------------------------


def test_question_level_report_returns_per_question_rows():
    _, _, session, _ = _session_with_attempts()
    report = Report.objects.create(
        title="Q-level",
        report_type="descriptive",
        scope="general",
        data_input_level="question",
        stat_conversion="percentage",
        include_section_breakdown=True,
        status="published",
    )
    data = generate_report_data(report, session)
    qb = data.get("question_breakdown")
    assert qb, "question-level report must return question_breakdown"
    assert len(qb) == 2
    by_label = {r["question_label"]: r for r in qb}
    assert by_label["Capital of France"]["percentage"] == 100.0
    assert by_label["2 + 2"]["percentage"] == 50.0
    assert by_label["2 + 2"]["question_id_label"] == "Q2"


def test_variable_level_report_has_no_question_breakdown():
    _, _, session, _ = _session_with_attempts()
    report = Report.objects.create(
        title="Var-level",
        report_type="descriptive",
        scope="general",
        data_input_level="level1",
        stat_conversion="percentage",
        include_section_breakdown=True,
        status="published",
    )
    data = generate_report_data(report, session)
    assert "question_breakdown" not in data
    assert data["section_breakdown"], "variable-level report still returns section rows"


def test_question_breakdown_renders_in_pdf_html():
    """The question breakdown reaches the PDF HTML builder (no weasyprint needed)."""
    from apps.reporting.pdf import _build_question_breakdown

    html = _build_question_breakdown(
        [
            {
                "question_id_label": "Q1",
                "question_label": "Capital of France",
                "section_title": "Verbal",
                "raw_score": 10.0,
                "max_score": 10.0,
                "percentage": 100.0,
                "converted_score": 100.0,
                "conversion_type": "percentage",
            }
        ]
    )
    assert "Question Breakdown" in html
    assert "Capital of France" in html
    assert "Q1" in html


# ---------------------------------------------------------------------------
# REP-1 — graph layout renders an SVG bar chart
# ---------------------------------------------------------------------------


def _session_two_sections():
    assessment = Assessment.objects.create(title="A", status="published")
    candidate = _make_user("graph@test.com")
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
    return assessment, session


def test_graph_layout_builds_bar_data():
    assessment, session = _session_two_sections()
    report = Report.objects.create(
        title="Graph",
        report_type="descriptive",
        scope="general",
        assessment=assessment,
        data_input_level="level1",
        stat_conversion="percentage",
        status="published",
    )
    ReportSection.objects.create(
        report=report,
        section_type="custom",
        title="Scores chart",
        order=1,
        table_graph_config={"layout": "graph", "table_title": "Aptitude"},
    )
    data = generate_report_data(report, session)
    section = next(s for s in data["sections"] if s.get("graph"))
    graph = section["graph"]
    assert graph["title"] == "Aptitude"
    assert len(graph["bars"]) == 2
    assert graph["max_value"] == 100.0
    verbal = next(b for b in graph["bars"] if b["variable"] == "Verbal")
    assert verbal["value"] == 90.0
    # No "scoped out" note is emitted any more.
    assert "graph_note" not in section


def test_graph_layout_renders_svg_in_pdf_html():
    from apps.reporting.pdf import _build_layout_graph_svg

    svg = _build_layout_graph_svg(
        {
            "title": "Aptitude",
            "bars": [
                {"variable": "Verbal", "value": 90.0, "colour_code": "#22c55e", "label": "High"},
                {"variable": "Numerical", "value": 40.0, "colour_code": "#ef4444", "label": "Low"},
            ],
            "max_value": 100.0,
        }
    )
    assert "<svg" in svg
    assert "Verbal" in svg and "Numerical" in svg
    assert "#22c55e" in svg  # band colour drives the bar fill
