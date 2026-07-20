"""Tests for the PDF report renderer.

Covers the WeasyPrint-based render_report_pdf() in apps/reporting/pdf.py.
The tests don't compare exact bytes (WeasyPrint output varies by version)
but verify:
  - The function returns non-empty PDF bytes
  - The PDF starts with the %PDF magic header
  - Different report types (descriptive/typological/interpretative/group)
    render without errors
  - Profiling data (FMI/VMI) renders
  - Custom narrative sections render
  - Empty/minimal data doesn't crash
"""

import pytest

from apps.reporting.pdf import render_report_pdf

pytestmark = pytest.mark.django_db


def _is_pdf(data: bytes) -> bool:
    """PDF files start with %PDF-."""
    return data.startswith(b"%PDF-") and len(data) > 100


def test_minimal_report_renders_pdf():
    """A report with just title + candidate renders a valid PDF."""
    data = {
        "report_title": "Test Report",
        "report_type": "descriptive",
        "scope": "general",
        "assessment_title": "Test Assessment",
        "candidate": {"id": 1, "name": "Jane Doe", "email": "jane@test.com"},
        "session": {"id": 1, "started_at": "2026-07-20T10:00:00", "completed_at": "2026-07-20T11:00:00"},
        "scores": {"total_score": 7, "max_score": 10, "percentage": 70.0},
    }
    pdf = render_report_pdf(data)
    assert _is_pdf(pdf)


def test_descriptive_report_with_cutoffs_renders():
    """A descriptive report with cutoffs renders the cutoff table."""
    data = {
        "report_title": "Descriptive Report",
        "report_type": "descriptive",
        "candidate": {"name": "Candidate"},
        "session": {},
        "scores": {"total_score": 8, "max_score": 10, "percentage": 80.0},
        "score_summary": {"total": 8, "max": 10, "percentage": 80.0, "passed": True},
        "section_breakdown": [
            {
                "section_title": "Abstract",
                "raw_score": 8,
                "max_score": 10,
                "percentage": 80.0,
                "converted_score": 80.0,
                "conversion_type": "percentage",
            },
        ],
        "descriptive": {
            "cutoffs": [
                {
                    "variable": "Abstract",
                    "candidate_score": 80.0,
                    "cutoff_score": 50.0,
                    "cutoff_label": "Average",
                    "is_above_cutoff": True,
                    "description": "Above average performance.",
                },
            ]
        },
    }
    pdf = render_report_pdf(data)
    assert _is_pdf(pdf)


def test_typological_report_renders():
    """A typological report with top variables renders."""
    data = {
        "report_title": "Personality Profile",
        "report_type": "typological",
        "candidate": {"name": "Test"},
        "session": {},
        "typological": {
            "type_profile": "ABC",
            "top_variables": [
                {"variable": "Verbal", "code": "A", "score": 90.0},
                {"variable": "Numerical", "code": "B", "score": 85.0},
                {"variable": "Spatial", "code": "C", "score": 80.0},
            ],
        },
    }
    pdf = render_report_pdf(data)
    assert _is_pdf(pdf)


def test_interpretative_report_renders():
    """An interpretative report with bands renders."""
    data = {
        "report_title": "Interpretative Report",
        "report_type": "interpretative",
        "candidate": {"name": "Test"},
        "session": {},
        "interpretative": {
            "bands": [
                {
                    "variable": "Abstract",
                    "candidate_score": 75.0,
                    "band_number": 1,
                    "band_label": "High",
                    "range": "70-100",
                    "description": "Strong abstract reasoning.",
                    "colour_code": "#16a34a",
                },
            ]
        },
    }
    pdf = render_report_pdf(data)
    assert _is_pdf(pdf)


def test_group_report_renders():
    """A group report with aggregated stats renders."""
    data = {
        "report_title": "Team Report",
        "report_type": "group",
        "candidate": {"name": "—"},
        "session": {},
        "group": {
            "candidate_count": 5,
            "average_score": 7.2,
            "average_percentage": 72.0,
            "min_score": 4.0,
            "max_score": 9.5,
            "min_percentage": 40.0,
            "max_percentage": 95.0,
            "pass_threshold": 40.0,
            "pass_rate": 80.0,
            "pass_count": 4,
            "section_averages": [
                {
                    "section_id": 1,
                    "section_title": "Verbal",
                    "average_percentage": 75.0,
                    "min_percentage": 50.0,
                    "max_percentage": 95.0,
                    "candidate_count": 5,
                },
            ],
            "distribution": {
                "fail (0-40)": 1,
                "below_avg (40-60)": 0,
                "average (60-80)": 2,
                "above_avg (80-100)": 2,
            },
            "candidates": [
                {"id": 1, "name": "Alice", "email": "a@t.com", "total_score": 9.5, "percentage": 95.0, "session_id": 1},
                {"id": 2, "name": "Bob", "email": "b@t.com", "total_score": 4.0, "percentage": 40.0, "session_id": 2},
            ],
        },
    }
    pdf = render_report_pdf(data)
    assert _is_pdf(pdf)


def test_profiling_report_renders():
    """A profiling report with FMI + VMI renders."""
    data = {
        "report_title": "Career Match Report",
        "report_type": "descriptive",
        "scope": "profiling",
        "candidate": {"name": "Jane"},
        "session": {},
        "profiling": {
            "raw_summary": {"total_score": 7, "max_score": 10, "percentage": 70.0},
            "fmi": [
                {
                    "career_title": "Programmer",
                    "final_match_index": 88.5,
                    "variable_mapping_index": 90.0,
                },
                {
                    "career_title": "Analyst",
                    "final_match_index": 45.2,
                    "variable_mapping_index": 50.0,
                },
            ],
            "vmi": [
                {
                    "career_title": "Programmer",
                    "variable_details": [
                        {
                            "variable": "Abstract",
                            "assessment": "A1",
                            "criterion_band": "H",
                            "candidate_band": "H",
                            "vmi": 100.0,
                        },
                    ],
                },
            ],
        },
    }
    pdf = render_report_pdf(data)
    assert _is_pdf(pdf)


def test_polar_variables_render():
    """Polar variables (opposite-score computation) render."""
    data = {
        "report_title": "Polar Report",
        "report_type": "descriptive",
        "candidate": {"name": "Test"},
        "session": {},
        "polar": {
            "polar_variables": [
                {
                    "primary_variable": "Extroversion",
                    "primary_score": 85.0,
                    "opposite_variable": "Introversion",
                    "opposite_score": 15.0,
                },
            ]
        },
    }
    pdf = render_report_pdf(data)
    assert _is_pdf(pdf)


def test_custom_narrative_sections_render():
    """Custom ReportSection rows render as narrative blocks."""
    data = {
        "report_title": "Report with Sections",
        "report_type": "descriptive",
        "candidate": {"name": "Test"},
        "session": {},
        "sections": [
            {
                "section_type": "narrative",
                "title": "Recommendation",
                "content": "The candidate shows strong analytical skills.",
                "order": 0,
                "is_visible": True,
            },
            {
                "section_type": "narrative",
                "title": "Hidden Note",
                "content": "Should not appear in PDF.",
                "order": 1,
                "is_visible": False,
            },
        ],
    }
    pdf = render_report_pdf(data)
    assert _is_pdf(pdf)


def test_empty_data_does_not_crash():
    """An empty dict should still produce a valid PDF (with '—' everywhere)."""
    pdf = render_report_pdf({})
    assert _is_pdf(pdf)
