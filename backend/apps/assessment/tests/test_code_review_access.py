"""Code review (3 Oct 2026): assessment access findings.

- Nested routes (sections, section questions, psychometric groups) honour
  assessment visibility for CJ content too, and question-level content is
  readable by authors / Help Desk / managers only — never by candidates.
- Managers of an organization take the assessments licensed to it without
  paying (same predicate as visibility).
- CJ staff tagged to an exclusive organization do not see its private
  assessments.
- The default ``POST /api/assessments/sessions/`` (and PUT/PATCH/DELETE) is
  disabled; sessions start through ``start_session`` only.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
)
from apps.organizations.models import Organization, OrganizationAssignment, OrganizationMember
from apps.question_bank.models import Question

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


def _question(author):
    return Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Secret title",
        question_text_1="Secret question text?",
        scoring_type="BINARY",
        status="confirmed",
        created_by=author,
    )


def _with_question(assessment, question):
    section = AssessmentSection.objects.create(assessment=assessment, title="S", level=1, order=0)
    AssessmentQuestion.objects.create(section=section, question=question, order=0)
    return section


# ---------------------------------------------------------------------------
# Finding 1 — nested routes
# ---------------------------------------------------------------------------


def test_individual_cannot_read_nested_routes_of_a_draft(roles):
    cja = _user(roles, "cj_admin", "cja@t.com")
    ind = _user(roles, "individual", "ind@t.com")
    draft = Assessment.objects.create(title="Draft", status="draft", created_by=cja)
    sec = _with_question(draft, _question(cja))

    client = _c(ind)
    assert client.get(f"/api/assessments/{draft.id}/").status_code == 404
    assert client.get(f"/api/assessments/{draft.id}/sections/").status_code == 404
    assert (
        client.get(f"/api/assessments/{draft.id}/sections/{sec.id}/questions/").status_code == 404
    )
    assert client.get(f"/api/assessments/{draft.id}/psychometric-groups/").status_code == 404


def test_employee_cannot_read_questions_of_an_unlicensed_assessment(roles):
    cja = _user(roles, "cj_admin", "cja@t.com")
    org = Organization.objects.create(name="Corp", type="corporate")
    emp = _user(roles, "individual", "emp@t.com")
    OrganizationMember.objects.create(organization=org, user=emp)
    unlicensed = Assessment.objects.create(title="U", status="published", created_by=cja)
    sec = _with_question(unlicensed, _question(cja))

    client = _c(emp)
    assert client.get(f"/api/assessments/{unlicensed.id}/").status_code == 404
    assert client.get(f"/api/assessments/{unlicensed.id}/sections/").status_code == 404
    assert (
        client.get(f"/api/assessments/{unlicensed.id}/sections/{sec.id}/questions/").status_code
        == 404
    )


def test_candidate_sees_sections_but_not_question_content_of_a_visible_assessment(roles):
    cja = _user(roles, "cj_admin", "cja@t.com")
    ind = _user(roles, "individual", "ind@t.com")
    published = Assessment.objects.create(title="P", status="published", created_by=cja)
    sec = _with_question(published, _question(cja))

    client = _c(ind)
    # Variable structure — the same as the retrieve returns.
    assert client.get(f"/api/assessments/{published.id}/sections/").status_code == 200
    # The test content itself comes only through his own session.
    resp = client.get(f"/api/assessments/{published.id}/sections/{sec.id}/questions/")
    assert resp.status_code == 403
    assert "Secret question text" not in str(resp.data)
    assert client.get(f"/api/assessments/{published.id}/psychometric-groups/").status_code == 403


def test_authors_helpdesk_and_managers_still_read_question_configuration(roles):
    cja = _user(roles, "cj_admin", "cja@t.com")
    psy = _user(roles, "psychometrician", "psy@t.com")
    hd = _user(roles, "helpdesk", "hd@t.com")
    org = Organization.objects.create(name="Corp", type="corporate")
    ca = _user(roles, "corp_admin", "ca@t.com")
    OrganizationMember.objects.create(organization=org, user=ca, is_admin=True)
    published = Assessment.objects.create(title="P", status="published", created_by=cja)
    OrganizationAssignment.objects.create(
        organization=org, item_type="assessment", item_id=published.id
    )
    sec = _with_question(published, _question(cja))
    url = f"/api/assessments/{published.id}/sections/{sec.id}/questions/"
    for user in (cja, psy, hd, ca):
        assert _c(user).get(url).status_code == 200, user.role.name


def test_trainer_cannot_reach_another_authors_assessment_sections(roles):
    cja = _user(roles, "cj_admin", "cja@t.com")
    tr = _user(roles, "trainer", "tr@t.com")
    other = Assessment.objects.create(title="Other", status="draft", created_by=cja)
    sec = _with_question(other, _question(cja))
    client = _c(tr)
    assert client.get(f"/api/assessments/{other.id}/sections/").status_code == 404
    resp = client.patch(
        f"/api/assessments/{other.id}/sections/{sec.id}/", {"title": "Hijack"}, format="json"
    )
    assert resp.status_code == 404
    sec.refresh_from_db()
    assert sec.title == "S"


def test_section_questions_route_requires_the_section_to_belong_to_the_assessment(roles):
    cja = _user(roles, "cj_admin", "cja@t.com")
    tr = _user(roles, "trainer", "tr@t.com")
    own = Assessment.objects.create(title="Own", status="draft", created_by=tr)
    other = Assessment.objects.create(title="Other", status="draft", created_by=cja)
    other_sec = _with_question(other, _question(cja))
    # The trainer sees his own assessment; the section id is someone else's.
    resp = _c(tr).get(f"/api/assessments/{own.id}/sections/{other_sec.id}/questions/")
    assert resp.status_code == 200
    body = resp.data.get("data", resp.data)
    results = body["results"] if isinstance(body, dict) and "results" in body else body
    assert results == []


# ---------------------------------------------------------------------------
# Finding 4 — managers take licensed priced assessments without paying
# ---------------------------------------------------------------------------


def test_corp_admin_licensed_priced_assessment_is_unlocked(roles):
    org = Organization.objects.create(name="Corp", type="corporate")
    ca = _user(roles, "corp_admin", "ca@t.com")
    OrganizationMember.objects.create(organization=org, user=ca, is_admin=True)
    licensed = Assessment.objects.create(title="Licensed", status="published", price=500)
    OrganizationAssignment.objects.create(
        organization=org, item_type="assessment", item_id=licensed.id
    )
    client = _c(ca)
    rows = client.get("/api/assessments/").data["data"]["results"]
    assert [(r["id"], r["is_unlocked"]) for r in rows] == [(licensed.id, True)]
    assert client.post(f"/api/assessments/{licensed.id}/start_session/").status_code in (
        200,
        201,
    )


# ---------------------------------------------------------------------------
# Finding 5 — CJ staff tagged to an exclusive organization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["cj_admin", "helpdesk", "psychometrician", "trainer"])
def test_cj_staff_member_of_exclusive_org_does_not_see_private_assessments(roles, role):
    org = Organization.objects.create(name="Excl", type="corp_exclusive")
    staff = _user(roles, role, f"{role}@t.com")
    OrganizationMember.objects.create(organization=org, user=staff)
    private = Assessment.objects.create(title="Private", status="published", owner_organization=org)
    client = _c(staff)
    assert client.get(f"/api/assessments/{private.id}/").status_code == 404
    ids = [r["id"] for r in client.get("/api/assessments/").data["data"]["results"]]
    assert private.id not in ids


def test_exclusive_org_member_still_sees_its_published_private_assessments(roles):
    org = Organization.objects.create(name="Excl", type="corp_exclusive")
    member = _user(roles, "individual", "m@t.com")
    OrganizationMember.objects.create(organization=org, user=member)
    private = Assessment.objects.create(title="Private", status="published", owner_organization=org)
    assert _c(member).get(f"/api/assessments/{private.id}/").status_code == 200


# ---------------------------------------------------------------------------
# Finding 7 — default session create / update / delete disabled
# ---------------------------------------------------------------------------


def test_default_session_create_is_not_allowed(roles):
    ind = _user(roles, "individual", "ind@t.com")
    priced = Assessment.objects.create(title="Priced", status="published", price=500)
    free = Assessment.objects.create(title="Free", status="published")
    client = _c(ind)
    for a in (priced, free):
        resp = client.post("/api/assessments/sessions/", {"assessment": a.id}, format="json")
        assert resp.status_code == 405
    assert not AssessmentSession.objects.filter(candidate=ind).exists()
    # The real flow still works.
    assert client.post(f"/api/assessments/{free.id}/start_session/").status_code in (200, 201)
    assert AssessmentSession.objects.filter(candidate=ind, assessment=free).count() == 1


def test_candidate_cannot_rewrite_or_delete_his_session(roles):
    ind = _user(roles, "individual", "ind@t.com")
    a = Assessment.objects.create(title="A", status="published")
    session = AssessmentSession.objects.create(assessment=a, candidate=ind, status="completed")
    client = _c(ind)
    url = f"/api/assessments/sessions/{session.id}/"
    assert client.patch(url, {"status": "active"}, format="json").status_code == 405
    assert (
        client.put(url, {"assessment": a.id, "status": "active"}, format="json").status_code == 405
    )
    assert client.delete(url).status_code == 405
    session.refresh_from_db()
    assert session.status == "completed"
    assert client.get(url).status_code == 200
