"""PSY-A1: psychometric group DELIVERY + SCORING (signed Approach 1).

Covers the session-engine integration that closes the remaining PSY-A1 gap:
groups are delivered to the candidate through the existing rank / forced-choice
renderers (as synthetic session-questions), answered on their own response
store, and scored per item to that item's explicitly-assigned section — never
via free-text option tags.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.assessment.models import (
    Assessment,
    AssessmentSection,
    AssessmentSession,
    PsychometricGroup,
    PsychometricGroupItem,
    PsychometricGroupResponse,
    SectionScore,
)
from apps.assessment.scoring import calculate_session_scores, score_psychometric_group
from apps.question_bank.models import Question

pytestmark = pytest.mark.django_db


def _statement(title):
    return Question.objects.create(
        question_type="PSYCHOMETRIC_STATEMENT",
        question_title=title,
        question_text_1=title,
        scoring_type="RANK",
        status="confirmed",
    )


def _candidate():
    role, _ = Role.objects.get_or_create(name="individual", defaults={"is_system": True})
    return User.objects.create_user(email="cand@t.com", password="pw", is_active=True, role=role)


def _rank_group(assessment, sections, statements, group_type="rank_simple", scale=None):
    group = PsychometricGroup.objects.create(
        assessment=assessment,
        group_type=group_type,
        group_number=1,
        rating_scale_points=scale,
    )
    items = [
        PsychometricGroupItem.objects.create(
            group=group, statement=statements[i], section=sections[i], order=i
        )
        for i in range(len(statements))
    ]
    return group, items


def _psy_assessment(n_sections=4):
    a = Assessment.objects.create(title="Psy", assessment_type="psychometric", status="published")
    secs = [
        AssessmentSection.objects.create(assessment=a, title=f"Var{i}", level=1, order=i)
        for i in range(n_sections)
    ]
    return a, secs


# --------------------------------------------------------------------------
# Pure scoring function
# --------------------------------------------------------------------------


def test_score_rank_group_routes_per_item_section():
    a, secs = _psy_assessment(4)
    stmts = [_statement(f"S{i}") for i in range(4)]
    group, items = _rank_group(a, secs, stmts)

    # Rank order = items[0], items[1], items[2], items[3].
    # Position 0 -> 4, 1 -> 3, 2 -> 2, 3 -> 1. Each item's section max = 4.
    ranking = [items[0].id, items[1].id, items[2].id, items[3].id]
    by_section = score_psychometric_group(group, {"ranking": ranking})

    assert by_section[secs[0].id] == (4.0, 4.0)
    assert by_section[secs[1].id] == (3.0, 4.0)
    assert by_section[secs[2].id] == (2.0, 4.0)
    assert by_section[secs[3].id] == (1.0, 4.0)


def test_score_forced_choice_single_selection_vs_non_selection():
    a, secs = _psy_assessment(2)
    s1, s2 = _statement("a"), _statement("b")
    group, items = _rank_group(a, [secs[0], secs[1]], [s1, s2], "forced_choice_single")

    by_section = score_psychometric_group(group, {"selected_option_id": items[0].id})
    # Selected item's section earns 1, the other 0; each item max = 1.
    assert by_section[secs[0].id] == (1.0, 1.0)
    assert by_section[secs[1].id] == (0.0, 1.0)


def test_score_forced_choice_two_level_uses_rating():
    a, secs = _psy_assessment(2)
    s1, s2 = _statement("a"), _statement("b")
    group, items = _rank_group(a, [secs[0], secs[1]], [s1, s2], "forced_choice_two_level", scale=5)
    by_section = score_psychometric_group(group, {"selected_option_id": items[1].id, "rating": 4})
    # Selected earns its rating (4), the other 0; each item max = max_rating (5).
    assert by_section[secs[1].id] == (4.0, 5.0)
    assert by_section[secs[0].id] == (0.0, 5.0)


def test_unanswered_group_scores_zero_but_keeps_max():
    a, secs = _psy_assessment(4)
    stmts = [_statement(f"S{i}") for i in range(4)]
    group, _items = _rank_group(a, secs, stmts)
    by_section = score_psychometric_group(group, None)
    for s in secs:
        assert by_section[s.id] == (0.0, 4.0)


# --------------------------------------------------------------------------
# Delivery + scoring through the session engine
# --------------------------------------------------------------------------


def test_group_delivered_as_synthetic_session_question():
    a, secs = _psy_assessment(4)
    stmts = [_statement(f"S{i}") for i in range(4)]
    group, items = _rank_group(a, secs, stmts)
    cand = _candidate()
    session = AssessmentSession.objects.create(assessment=a, candidate=cand, status="active")

    client = APIClient()
    client.force_authenticate(cand)
    resp = client.get(f"/api/assessments/sessions/{session.id}/questions/")
    assert resp.status_code == 200, resp.data
    data = resp.data["data"]

    group_units = [u for u in data if u.get("group_id") == group.id]
    assert len(group_units) == 1
    unit = group_units[0]
    assert unit["question"] == -group.id
    assert unit["question_detail"]["question_type"] == "RANK_SIMPLE"
    opts = unit["question_detail"]["options"]
    assert len(opts) == 4
    assert {o["id"] for o in opts} == {it.id for it in items}
    assert all(o["option_type"] == "RANK" for o in opts)
    # A response row was seeded.
    assert PsychometricGroupResponse.objects.filter(session=session, group=group).exists()


def test_answer_group_endpoint_persists_and_scores():
    a, secs = _psy_assessment(4)
    stmts = [_statement(f"S{i}") for i in range(4)]
    group, items = _rank_group(a, secs, stmts)
    cand = _candidate()
    session = AssessmentSession.objects.create(assessment=a, candidate=cand, status="active")

    client = APIClient()
    client.force_authenticate(cand)
    ranking = [items[0].id, items[1].id, items[2].id, items[3].id]
    resp = client.post(
        f"/api/assessments/sessions/{session.id}/answer-group/",
        {"group_id": group.id, "raw_answer": {"ranking": ranking}},
        format="json",
    )
    assert resp.status_code == 200, resp.data

    stored = PsychometricGroupResponse.objects.get(session=session, group=group)
    assert stored.status == "attempted"
    assert stored.raw_answer == {"ranking": ranking}

    calculate_session_scores(session)
    scores = {
        ss.section_id: (ss.raw_score, ss.max_score)
        for ss in SectionScore.objects.filter(session=session)
    }
    assert scores[secs[0].id] == (4.0, 4.0)
    assert scores[secs[3].id] == (1.0, 4.0)
    session.refresh_from_db()
    assert session.max_score == 16.0  # 4 sections x 4
    assert session.total_score == 10.0  # 4+3+2+1


def test_answer_group_rejects_foreign_group():
    a, secs = _psy_assessment(2)
    other, osecs = _psy_assessment(2)
    s1, s2 = _statement("a"), _statement("b")
    ogroup, _ = _rank_group(other, osecs, [s1, s2], "forced_choice_single")
    cand = _candidate()
    session = AssessmentSession.objects.create(assessment=a, candidate=cand, status="active")

    client = APIClient()
    client.force_authenticate(cand)
    resp = client.post(
        f"/api/assessments/sessions/{session.id}/answer-group/",
        {"group_id": ogroup.id, "raw_answer": {"selected_option_id": 1}},
        format="json",
    )
    assert resp.status_code == 404
