"""Code review (3 Oct 2026): question-bank findings.

- reviewer-options is refused for private questions / private authors (no
  CJ reviewer pool shown to an exclusive organization).
- A psychometrician's "Assigned to me" lists only questions actually with
  him (pending psychometric review); his decision clears the routing.
- Non-integer ``?category`` / ``?parent`` filters are a 400, not a 500.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.organizations.models import Organization, OrganizationMember
from apps.question_bank.models import Category, Question

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _user(roles, role, email):
    return User.objects.create_user(
        email=email, password="pw", is_active=True, role=roles[role], full_name=email
    )


def _c(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _statement(author, cat, **kw):
    data = {
        "category": cat,
        "created_by": author,
        "question_type": "PSYCHOMETRIC_STATEMENT",
        "scoring_type": "",
        "question_title": "T",
        "question_text_1": "Q?",
    }
    data.update(kw)
    return Question.objects.create(**data)


def _review(user, q, review_type, action):
    payload = {"review_type": review_type, "action": action}
    if action == "approve":
        payload["rating"] = 4
    if action == "send_back":
        payload["comment"] = "fix"
    resp = _c(user).post(f"/api/question-bank/questions/{q.id}/review/", payload, format="json")
    assert resp.status_code == 200, resp.content
    q.refresh_from_db()
    return q


def _mine(user):
    body = _c(user).get("/api/question-bank/questions/?assigned=me").json()["data"]
    return [r["id"] for r in body["results"]]


# ---------------------------------------------------------------------------
# Finding 2 — reviewer-options for private questions
# ---------------------------------------------------------------------------


def test_exclusive_admin_cannot_list_cj_reviewers(roles):
    org = Organization.objects.create(name="Excl", type="corp_exclusive")
    xa = _user(roles, "corp_exclusive", "xa@t.com")
    OrganizationMember.objects.create(organization=org, user=xa, is_admin=True)
    _user(roles, "reviewer", "rev@t.com")
    q = _statement(xa, None, owner_organization=org, status="confirmed")
    resp = _c(xa).get(f"/api/question-bank/questions/{q.id}/reviewer-options/")
    assert resp.status_code == 403
    assert "rev@t.com" not in str(resp.data)


def test_sme_still_lists_reviewers_for_a_cj_question(roles):
    sme = _user(roles, "sme", "sme@t.com")
    rev = _user(roles, "reviewer", "rev@t.com")
    q = _statement(sme, Category.objects.create(name="D"))
    resp = _c(sme).get(f"/api/question-bank/questions/{q.id}/reviewer-options/")
    assert resp.status_code == 200
    assert [r["id"] for r in resp.data["data"]["reviewers"]] == [rev.id]


# ---------------------------------------------------------------------------
# Finding 3 — psychometrician "Assigned to me"
# ---------------------------------------------------------------------------


def test_psychometrician_queue_only_holds_questions_pending_with_him(roles):
    sme = _user(roles, "sme", "sme@t.com")
    rev = _user(roles, "reviewer", "rev@t.com")
    psy = _user(roles, "psychometrician", "psy@t.com")
    q = _statement(sme, Category.objects.create(name="D"))
    sme_client = _c(sme)
    assert (
        sme_client.post(
            f"/api/question-bank/questions/{q.id}/submit_for_review/",
            {"reviewer": rev.id},
            format="json",
        ).status_code
        == 200
    )
    q = _review(rev, q, "content", "approve")
    q = _review(psy, q, "psychometric", "send_back")
    assert q.status == "sent_back"
    assert q.assigned_psychometrician == psy
    # With the SME, not with him.
    assert _mine(psy) == []

    assert (
        sme_client.post(f"/api/question-bank/questions/{q.id}/submit_for_review/").status_code
        == 200
    )
    q.refresh_from_db()
    assert _mine(psy) == []  # in content review
    q = _review(rev, q, "content", "approve")
    assert _mine(psy) == [q.id]  # back with him

    q = _review(psy, q, "psychometric", "approve")
    assert q.status == "confirmed"
    assert q.assigned_psychometrician is None
    assert _mine(psy) == []


# ---------------------------------------------------------------------------
# Finding 6 — non-integer filters
# ---------------------------------------------------------------------------


def test_non_integer_category_filter_is_a_400(roles):
    sme = _user(roles, "sme", "sme@t.com")
    resp = _c(sme).get("/api/question-bank/questions/?category=abc")
    assert resp.status_code == 400


def test_non_integer_parent_filter_is_a_400(roles):
    cja = _user(roles, "cj_admin", "cja@t.com")
    resp = _c(cja).get("/api/question-bank/categories/?parent=abc")
    assert resp.status_code == 400


def test_integer_and_root_filters_still_work(roles):
    cja = _user(roles, "cj_admin", "cja@t.com")
    root = Category.objects.create(name="Root")
    child = Category.objects.create(name="Child", parent=root)
    q = _statement(cja, child)
    client = _c(cja)
    resp = client.get(f"/api/question-bank/questions/?category={root.id}")
    assert resp.status_code == 200
    assert [r["id"] for r in resp.json()["data"]["results"]] == [q.id]
    resp = client.get("/api/question-bank/categories/?parent=root")
    assert resp.status_code == 200
    resp = client.get(f"/api/question-bank/categories/?parent={root.id}")
    assert resp.status_code == 200
