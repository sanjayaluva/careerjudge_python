"""PSY-A1: signed Approach-1 psychometric grouping (config layer)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role, User
from apps.assessment.models import Assessment, AssessmentSection, PsychometricGroup
from apps.question_bank.models import Question

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(db):
    role, _ = Role.objects.get_or_create(name="cj_admin", defaults={"is_system": True})
    for a in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="assessment", action=a)
    u = User.objects.create_user(email="psyadmin@t.com", password="pw", is_active=True, role=role)
    c = APIClient()
    c.force_authenticate(u)
    return c


def _statement(title):
    return Question.objects.create(
        question_type="PSYCHOMETRIC_STATEMENT", question_title=title,
        question_text_1=title, scoring_type="RANK", status="confirmed",
    )


def _setup():
    a = Assessment.objects.create(title="Psy", assessment_type="psychometric", status="draft")
    secs = [
        AssessmentSection.objects.create(assessment=a, title=f"Var{i}", level=1, order=i)
        for i in range(1, 5)
    ]
    return a, secs


def test_create_rank_group_one_per_section(admin_client):
    a, secs = _setup()
    stmts = [_statement(f"S{i}") for i in range(4)]
    resp = admin_client.post(
        f"/api/assessments/{a.id}/psychometric-groups/",
        {
            "group_type": "rank_simple",
            "group_number": 1,
            "items": [{"statement": stmts[i].id, "section": secs[i].id} for i in range(4)],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    g = PsychometricGroup.objects.get(assessment=a)
    assert g.items.count() == 4
    assert {it.section_id for it in g.items.all()} == {s.id for s in secs}


def test_rank_group_rejects_repeated_section(admin_client):
    a, secs = _setup()
    s1, s2 = _statement("a"), _statement("b")
    resp = admin_client.post(
        f"/api/assessments/{a.id}/psychometric-groups/",
        {
            "group_type": "rank_simple",
            "items": [
                {"statement": s1.id, "section": secs[0].id},
                {"statement": s2.id, "section": secs[0].id},  # same section!
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "one statement per section" in str(resp.data).lower()


def test_forced_choice_pair_two_different_sections(admin_client):
    a, secs = _setup()
    s1, s2 = _statement("a"), _statement("b")
    resp = admin_client.post(
        f"/api/assessments/{a.id}/psychometric-groups/",
        {
            "group_type": "forced_choice_single",
            "items": [
                {"statement": s1.id, "section": secs[0].id},
                {"statement": s2.id, "section": secs[1].id},
            ],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data


def test_forced_choice_rejects_same_section(admin_client):
    a, secs = _setup()
    s1, s2 = _statement("a"), _statement("b")
    resp = admin_client.post(
        f"/api/assessments/{a.id}/psychometric-groups/",
        {
            "group_type": "forced_choice_single",
            "items": [
                {"statement": s1.id, "section": secs[0].id},
                {"statement": s2.id, "section": secs[0].id},
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "two different sections" in str(resp.data).lower()


def test_rejects_non_statement_question(admin_client):
    a, secs = _setup()
    bad = Question.objects.create(
        question_type="RANK_SIMPLE", question_title="tmpl", question_text_1="x",
        scoring_type="RANK", status="confirmed",
    )
    s1 = _statement("a")
    resp = admin_client.post(
        f"/api/assessments/{a.id}/psychometric-groups/",
        {
            "group_type": "forced_choice_single",
            "items": [
                {"statement": bad.id, "section": secs[0].id},
                {"statement": s1.id, "section": secs[1].id},
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "not a psychometric statement" in str(resp.data).lower()
