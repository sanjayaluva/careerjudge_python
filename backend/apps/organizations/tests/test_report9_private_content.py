"""Report 9 (1 Oct 2026) — Corporate Exclusive organizations' private content.

#34/#53 own organizations, #39/#40 private question bank, #41/#42 private
assessments, #43/#44 private reports, #47 private courses, #51/#52 members
take / learn them, #95 the "exclusive environment".

Isolation follows Report 4 §3 (13 Aug 2026): "No one, including CJ Admin,
should have ACCESS to the exclusive platform's contents", and the exclusive
organization has no access to CJ's question bank or reports (CJ assessments
and courses only through CJ Admin's licensing). The superuser keeps access.

Rights come from the real role table, exactly as in production.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import (
    Assessment,
    AssessmentModificationRequest,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
)
from apps.organizations.models import Organization, OrganizationAssignment, OrganizationMember
from apps.question_bank.models import Category, Question, QuestionBankDeletionRequest
from apps.reporting.models import Report
from apps.training.models import CourseRegistration, TrainingCourse

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _auth(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


def _user(roles, role, email, **extra):
    return User.objects.create_user(
        email=email,
        password="pw",
        is_active=True,
        role=roles[role] if role else None,
        full_name=email,
        **extra,
    )


def _data(resp):
    body = resp.data.get("data", resp.data)
    return body["results"] if isinstance(body, dict) and "results" in body else body


def _ids(resp):
    assert resp.status_code == 200, resp.data
    rows = _data(resp)
    ids = set()

    def walk(items):
        for row in items:
            ids.add(row["id"])
            walk(row.get("subcategories") or [])

    walk(rows)
    return ids


def _space(owner, tag):
    """One content space: a category, a question, a draft and a published
    assessment (with the question), a report and a draft + published course."""
    cat = Category.objects.create(name=f"{tag} cat", owner_organization=owner)
    q = Question.objects.create(
        category=cat,
        owner_organization=owner,
        question_type="MCQ_TEXT_IMAGE",
        question_title=f"{tag} q",
        question_text_1=f"{tag} question",
        status="confirmed",
    )
    asm = Assessment.objects.create(title=f"{tag} asm", status="published", owner_organization=owner)
    sec = AssessmentSection.objects.create(assessment=asm, title="S1", level=1)
    AssessmentQuestion.objects.create(section=sec, question=q)
    draft = Assessment.objects.create(title=f"{tag} draft", owner_organization=owner)
    rep = Report.objects.create(title=f"{tag} report", assessment=asm, owner_organization=owner)
    course = TrainingCourse.objects.create(
        title=f"{tag} course", status="published", owner_organization=owner
    )
    course_draft = TrainingCourse.objects.create(title=f"{tag} course draft", owner_organization=owner)
    return {
        "cat": cat,
        "q": q,
        "asm": asm,
        "draft": draft,
        "rep": rep,
        "course": course,
        "course_draft": course_draft,
    }


@pytest.fixture
def world(roles):
    org_a = Organization.objects.create(name="Excl A", type="corp_exclusive")
    org_b = Organization.objects.create(name="Excl B", type="corp_exclusive")
    corp = Organization.objects.create(name="Plain Corp", type="corporate")
    cp_org = Organization.objects.create(name="Partner", type="channel_partner")

    u = {
        "superuser": _user(roles, None, "su@t.com", is_superuser=True, is_staff=True),
        "cj_admin": _user(roles, "cj_admin", "cja@t.com"),
        "psychometrician": _user(roles, "psychometrician", "psy@t.com"),
        "sme": _user(roles, "sme", "sme@t.com"),
        "reviewer": _user(roles, "reviewer", "rev@t.com"),
        "trainer": _user(roles, "trainer", "trn@t.com"),
        "counsellor": _user(roles, "counsellor", "cns@t.com"),
        "helpdesk": _user(roles, "helpdesk", "hd@t.com"),
        "corp_admin": _user(roles, "corp_admin", "ca@t.com"),
        "channel_partner": _user(roles, "channel_partner", "cp@t.com"),
        "individual": _user(roles, "individual", "ind@t.com"),
        "excl_a": _user(roles, "corp_exclusive", "xa@t.com"),
        "member_a": _user(roles, "individual", "ma@t.com"),
        "excl_b": _user(roles, "corp_exclusive", "xb@t.com"),
        "member_b": _user(roles, "individual", "mb@t.com"),
    }
    OrganizationMember.objects.create(organization=org_a, user=u["excl_a"], is_admin=True)
    OrganizationMember.objects.create(organization=org_a, user=u["member_a"])
    OrganizationMember.objects.create(organization=org_b, user=u["excl_b"], is_admin=True)
    OrganizationMember.objects.create(organization=org_b, user=u["member_b"])
    OrganizationMember.objects.create(organization=corp, user=u["corp_admin"], is_admin=True)
    OrganizationMember.objects.create(organization=cp_org, user=u["channel_partner"], is_admin=True)

    cj = _space(None, "CJ")
    a = _space(org_a, "A")
    b = _space(org_b, "B")
    cj_draft = cj["draft"]
    # CJ Admin licensed one CJ assessment and course to organization A.
    OrganizationAssignment.objects.create(
        organization=org_a, item_type="assessment", item_id=cj["asm"].id
    )
    OrganizationAssignment.objects.create(
        organization=org_a, item_type="training_course", item_id=cj["course"].id
    )
    return {"u": u, "org_a": org_a, "org_b": org_b, "cj": cj, "a": a, "b": b, "cj_draft": cj_draft}


def _private_ids(world, key):
    return {world["a"][key].id, world["b"][key].id}


# ---------------------------------------------------------------------------
# Isolation: every listing shows each user exactly his space (Report 4 §3)
# ---------------------------------------------------------------------------

CJ_ROLES = (
    "cj_admin",
    "psychometrician",
    "sme",
    "reviewer",
    "trainer",
    "counsellor",
    "helpdesk",
    "corp_admin",
    "channel_partner",
    "individual",
)


def _get(world, who, url):
    return _auth(world["u"][who]).get(url)


@pytest.mark.parametrize("who", CJ_ROLES)
def test_cj_side_never_sees_private_content(world, who):
    private = {
        "/api/question-bank/categories/": _private_ids(world, "cat"),
        "/api/question-bank/categories/tree/": _private_ids(world, "cat"),
        "/api/question-bank/questions/": _private_ids(world, "q"),
        "/api/assessments/": _private_ids(world, "asm") | _private_ids(world, "draft"),
        "/api/assessments/?status=published": _private_ids(world, "asm"),
        "/api/reporting/reports/": _private_ids(world, "rep"),
        "/api/training/courses/": _private_ids(world, "course")
        | _private_ids(world, "course_draft"),
    }
    for url, ids in private.items():
        resp = _get(world, who, url)
        if resp.status_code == 403:  # the role has no right on this module
            continue
        assert not (_ids(resp) & ids), (who, url)
    # ... nor by id.
    for url in (
        f"/api/question-bank/questions/{world['a']['q'].id}/",
        f"/api/question-bank/categories/{world['a']['cat'].id}/",
        f"/api/assessments/{world['a']['asm'].id}/",
        f"/api/assessments/{world['a']['asm'].id}/sections/",
        f"/api/reporting/reports/{world['a']['rep'].id}/",
        f"/api/training/courses/{world['a']['course'].id}/",
    ):
        assert _get(world, who, url).status_code in (403, 404), (who, url)


def test_cj_admin_and_psychometrician_still_see_all_cj_content(world):
    cj = world["cj"]
    for who in ("cj_admin", "psychometrician"):
        assert cj["q"].id in _ids(_get(world, who, "/api/question-bank/questions/"))
        assert cj["cat"].id in _ids(_get(world, who, "/api/question-bank/categories/"))
        assert {cj["asm"].id, cj["draft"].id} <= _ids(_get(world, who, "/api/assessments/"))
        assert cj["rep"].id in _ids(_get(world, who, "/api/reporting/reports/"))
    assert {cj["course"].id, cj["course_draft"].id} <= _ids(
        _get(world, "cj_admin", "/api/training/courses/")
    )


def test_exclusive_admin_sees_only_his_space(world):
    a, cj = world["a"], world["cj"]
    get = lambda url: _ids(_get(world, "excl_a", url))  # noqa: E731
    assert get("/api/question-bank/categories/") == {a["cat"].id}
    assert get("/api/question-bank/categories/tree/") == {a["cat"].id}
    assert get("/api/question-bank/questions/") == {a["q"].id}
    # His assessments in every status + the CJ assessment licensed to him.
    assert get("/api/assessments/") == {a["asm"].id, a["draft"].id, cj["asm"].id}
    assert get("/api/reporting/reports/") == {a["rep"].id}
    assert get("/api/training/courses/") == {
        a["course"].id,
        a["course_draft"].id,
        cj["course"].id,
    }
    # Organization B's admin sees B only (no licensing for B).
    b = world["b"]
    assert _ids(_get(world, "excl_b", "/api/assessments/")) == {b["asm"].id, b["draft"].id}
    assert _ids(_get(world, "excl_b", "/api/question-bank/questions/")) == {b["q"].id}


def test_members_see_their_organizations_published_private_content(world):
    a, b, cj = world["a"], world["b"], world["cj"]
    assert _ids(_get(world, "member_a", "/api/assessments/")) == {a["asm"].id, cj["asm"].id}
    assert _ids(_get(world, "member_a", "/api/training/courses/")) == {
        a["course"].id,
        cj["course"].id,
    }
    assert _ids(_get(world, "member_b", "/api/assessments/")) == {b["asm"].id}
    assert _ids(_get(world, "member_b", "/api/training/courses/")) == {b["course"].id}


def test_superuser_keeps_access_for_support(world):
    ids = _ids(_get(world, "superuser", "/api/question-bank/questions/"))
    assert {world["a"]["q"].id, world["b"]["q"].id, world["cj"]["q"].id} <= ids
    ids = _ids(_get(world, "superuser", "/api/assessments/"))
    assert {world["a"]["asm"].id, world["b"]["asm"].id, world["cj"]["asm"].id} <= ids


def test_psychometric_extract_never_reaches_private_questions(world):
    psy = _auth(world["u"]["psychometrician"])
    url = "/api/question-bank/questions/psychometric-extract/"
    resp = psy.post(url, {"question_ids": [world["a"]["q"].id]}, format="json")
    assert resp.status_code == 400
    resp = psy.post(url, {"category_id": world["a"]["cat"].id}, format="json")
    assert resp.status_code == 400
    resp = psy.post(url, {"question_ref": str(world["a"]["q"].id)}, format="json")
    assert resp.status_code == 200 and resp.data["data"] == []
    resp = psy.post(url, {"category_id": world["cj"]["cat"].id}, format="json")
    assert [r["id"] for r in resp.data["data"]] == [world["cj"]["q"].id]
    # Report 4 §3: psychometric analysis is not an exclusive-environment right.
    resp = _auth(world["u"]["excl_a"]).post(
        url, {"question_ids": [world["a"]["q"].id]}, format="json"
    )
    assert resp.status_code == 400


def test_profiling_picker_and_selection_exclude_private_assessments(world):
    psy = _auth(world["u"]["psychometrician"])
    picker = _ids(psy.get("/api/assessments/?status=published"))
    assert world["cj"]["asm"].id in picker and not picker & _private_ids(world, "asm")
    sol = psy.post("/api/career-profiling/solutions/", {"title": "Sol"}, format="json")
    assert sol.status_code == 201, sol.data
    sid = sol.data["data"]["id"]
    resp = psy.post(
        f"/api/career-profiling/solutions/{sid}/assessments/",
        {"assessment": world["a"]["asm"].id, "label": "X"},
        format="json",
    )
    assert resp.status_code == 400


def test_private_content_cannot_be_licensed(world):
    cja = _auth(world["u"]["cj_admin"])
    resp = cja.post(
        f"/api/organizations/{world['org_b'].id}/assignments/",
        {"item_type": "assessment", "item_id": world["a"]["asm"].id},
        format="json",
    )
    assert resp.status_code == 400
    resp = cja.post(
        f"/api/organizations/{world['org_b'].id}/assignments/",
        {"item_type": "training_course", "item_id": world["a"]["course"].id},
        format="json",
    )
    assert resp.status_code == 400


def test_cj_admin_sessions_and_registrations_exclude_private(world):
    a = world["a"]
    member = world["u"]["member_a"]
    s = AssessmentSession.objects.create(assessment=a["asm"], candidate=member)
    reg = CourseRegistration.objects.create(course=a["course"], student=member)
    cja = _auth(world["u"]["cj_admin"])
    assert s.id not in _ids(cja.get("/api/assessments/sessions/"))
    assert reg.id not in _ids(cja.get("/api/training/registrations/"))
    assert cja.get(f"/api/training/lessons/?course={a['course'].id}").status_code == 200


# ---------------------------------------------------------------------------
# #34 / #53 — own organizations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("who,kind", [("excl_a", "corp_exclusive"), ("channel_partner", "channel_partner")])
def test_manager_creates_his_own_organization(world, who, kind):
    user = world["u"][who]
    c = _auth(user)
    resp = c.post(
        "/api/organizations/",
        {"name": f"New {kind}", "type": "corporate", "enabled_modules": ["training"]},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    org = Organization.objects.get(id=resp.data["data"]["id"])
    assert org.type == kind and org.enabled_modules is None
    assert OrganizationMember.objects.filter(organization=org, user=user, is_admin=True).exists()
    assert org.id in _ids(c.get("/api/organizations/"))
    # Only he (and CJ Admin) sees it.
    assert org.id in _ids(_auth(world["u"]["cj_admin"]).get("/api/organizations/"))
    for other in ("excl_b", "corp_admin", "member_a"):
        resp = _auth(world["u"][other]).get("/api/organizations/")
        assert resp.status_code == 403 or org.id not in _ids(resp)
    # He edits its details — not its type or modules — and cannot delete it.
    resp = c.patch(
        f"/api/organizations/{org.id}/",
        {"name": f"Renamed {kind}", "city": "Kochi", "type": "corporate", "enabled_modules": []},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    org.refresh_from_db()
    assert (org.name, org.city, org.type) == (f"Renamed {kind}", "Kochi", kind)
    assert c.delete(f"/api/organizations/{org.id}/").status_code == 403


def test_manager_cannot_edit_someone_elses_organization(world):
    c = _auth(world["u"]["excl_a"])
    assert c.patch(f"/api/organizations/{world['org_b'].id}/", {"name": "X"}).status_code == 404
    # Members (non-admin) of his organization cannot edit it either.
    resp = _auth(world["u"]["member_a"]).patch(
        f"/api/organizations/{world['org_a'].id}/", {"name": "X"}, format="json"
    )
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# #39 / #40 — private question bank
# ---------------------------------------------------------------------------


def test_exclusive_admin_builds_his_question_bank(world):
    org_a = world["org_a"]
    c = _auth(world["u"]["excl_a"])
    resp = c.post("/api/question-bank/categories/", {"name": "Aptitude"}, format="json")
    assert resp.status_code == 201, resp.data
    cat = Category.objects.get(id=resp.data["data"]["id"])
    assert cat.owner_organization_id == org_a.id
    sub = c.post(
        "/api/question-bank/categories/", {"name": "Numbers", "parent": cat.id}, format="json"
    )
    assert Category.objects.get(id=sub.data["data"]["id"]).owner_organization_id == org_a.id

    resp = c.post(
        "/api/question-bank/questions/",
        {
            "category": sub.data["data"]["id"],
            "question_type": "MCQ_TEXT_IMAGE",
            "question_title": "Sum",
            "question_text_1": "2+2?",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    q = Question.objects.get(id=resp.data["data"]["id"])
    # In his bank at once — no SME → Reviewer → Psychometrician workflow.
    assert (q.owner_organization_id, q.status) == (org_a.id, "confirmed")
    assert c.post(f"/api/question-bank/questions/{q.id}/submit_for_review/").status_code == 403
    # Edits and deletes directly, in any status.
    resp = c.patch(f"/api/question-bank/questions/{q.id}/", {"question_text_1": "3+3?"}, format="json")
    assert resp.status_code == 200, resp.data
    opts = c.post(
        f"/api/question-bank/questions/{q.id}/options/bulk/",
        {"options": [{"option_type": "TEXT", "text_value": "6", "is_correct": True}]},
        format="json",
    )
    assert opts.status_code == 200, opts.data
    assert c.delete(f"/api/question-bank/questions/{q.id}/").status_code == 200
    assert not Question.objects.filter(id=q.id).exists()
    assert c.delete(f"/api/question-bank/categories/{sub.data['data']['id']}/").status_code == 200
    assert not QuestionBankDeletionRequest.objects.exists()


def test_exclusive_admin_cannot_use_other_spaces(world):
    c = _auth(world["u"]["excl_a"])
    for cat in (world["cj"]["cat"], world["b"]["cat"]):
        resp = c.post(
            "/api/question-bank/questions/",
            {
                "category": cat.id,
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "x",
                "question_text_1": "x",
            },
            format="json",
        )
        assert resp.status_code == 400
        resp = c.post("/api/question-bank/categories/", {"name": "x", "parent": cat.id}, format="json")
        assert resp.status_code == 400
    # A CJ question's options are out of his reach; a CJ author's likewise for his.
    assert c.get(f"/api/question-bank/questions/{world['cj']['q'].id}/options/").status_code == 404
    sme = _auth(world["u"]["psychometrician"])
    assert sme.get(f"/api/question-bank/questions/{world['a']['q'].id}/options/").status_code == 404


# ---------------------------------------------------------------------------
# #41 / #42 — private assessments; #51 members take them
# ---------------------------------------------------------------------------


def test_exclusive_admin_builds_and_publishes_his_assessment(world):
    a, org_a = world["a"], world["org_a"]
    c = _auth(world["u"]["excl_a"])
    resp = c.post("/api/assessments/", {"title": "Private test"}, format="json")
    assert resp.status_code == 201, resp.data
    asm = Assessment.objects.get(id=resp.data["data"]["id"])
    assert asm.owner_organization_id == org_a.id
    sec = c.post(f"/api/assessments/{asm.id}/sections/", {"title": "S1", "duration_seconds": None}, format="json")
    assert sec.status_code == 201, sec.data
    base = f"/api/assessments/{asm.id}/sections/{sec.data['data']['id']}/questions/"
    assert c.post(base, {"question": world["cj"]["q"].id}, format="json").status_code == 400
    assert c.post(base, {"question": a["q"].id}, format="json").status_code == 201
    assert c.post(f"/api/assessments/{asm.id}/publish/").status_code == 200
    # CJ's post-publish approval does not apply in his environment.
    resp = c.patch(f"/api/assessments/{asm.id}/", {"title": "Renamed"}, format="json")
    assert resp.status_code == 200, resp.data
    asm.refresh_from_db()
    assert asm.title == "Renamed"
    assert not AssessmentModificationRequest.objects.exists()

    # His member takes it; another organization's member cannot.
    member = _auth(world["u"]["member_a"])
    assert member.post(f"/api/assessments/{asm.id}/start_session/").status_code == 201
    other = _auth(world["u"]["member_b"])
    assert other.post(f"/api/assessments/{asm.id}/start_session/").status_code == 404

    resp = c.delete(f"/api/assessments/{asm.id}/")
    assert resp.status_code == 200 and not Assessment.objects.filter(id=asm.id).exists()


def test_exclusive_admin_cannot_change_licensed_cj_assessment(world):
    cj_asm = world["cj"]["asm"]
    c = _auth(world["u"]["excl_a"])
    assert c.get(f"/api/assessments/{cj_asm.id}/").status_code == 200
    assert c.patch(f"/api/assessments/{cj_asm.id}/", {"title": "x"}, format="json").status_code == 403
    assert c.delete(f"/api/assessments/{cj_asm.id}/").status_code == 403
    resp = c.post(f"/api/assessments/{cj_asm.id}/sections/", {"title": "x"}, format="json")
    assert resp.status_code == 403
    assert not AssessmentModificationRequest.objects.exists()
    # ... and cannot reach organization B's assessment at all.
    assert c.get(f"/api/assessments/{world['b']['asm'].id}/sections/").status_code == 404


def test_cj_author_cannot_put_private_question_in_cj_assessment(world):
    psy = _auth(world["u"]["psychometrician"])
    draft = world["cj_draft"]
    sec = psy.post(f"/api/assessments/{draft.id}/sections/", {"title": "S"}, format="json")
    base = f"/api/assessments/{draft.id}/sections/{sec.data['data']['id']}/questions/"
    assert psy.post(base, {"question": world["a"]["q"].id}, format="json").status_code == 400


def test_exclusive_admin_schedules_private_assessment_for_his_members(world):
    a, org_a = world["a"], world["org_a"]
    payload = {"assessment": a["asm"].id, "scheduled_at": "2030-01-01T10:00:00Z"}
    url = f"/api/organizations/{org_a.id}/schedules/"
    resp = _auth(world["u"]["excl_a"]).post(url, payload, format="json")
    assert resp.status_code == 201, resp.data
    # CJ Admin neither sees that schedule nor schedules private assessments.
    cja = _auth(world["u"]["cj_admin"])
    assert _ids(cja.get(url)) == set()
    assert cja.post(url, payload, format="json").status_code == 403
    # Organization B's admin cannot schedule A's assessment for B.
    resp = _auth(world["u"]["excl_b"]).post(
        f"/api/organizations/{world['org_b'].id}/schedules/", payload, format="json"
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# #43 / #44 — private reports
# ---------------------------------------------------------------------------


def test_exclusive_admin_designs_reports_on_his_assessments(world):
    a, org_a = world["a"], world["org_a"]
    c = _auth(world["u"]["excl_a"])
    payload = {"title": "R", "report_type": "descriptive", "scope": "general"}
    resp = c.post("/api/reporting/reports/", {**payload, "assessment": a["asm"].id}, format="json")
    assert resp.status_code == 201, resp.data
    rid = resp.data["data"]["id"]
    assert Report.objects.get(id=rid).owner_organization_id == org_a.id
    resp = c.post("/api/reporting/reports/", {**payload, "assessment": world["cj"]["asm"].id}, format="json")
    assert resp.status_code == 400
    sec = a["asm"].sections.first()
    resp = c.post(
        f"/api/reporting/reports/{rid}/cutoffs/",
        {"section": sec.id, "cutoff_score": 5, "cutoff_label": "High"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert c.post(f"/api/reporting/reports/{rid}/publish/").status_code == 200
    assert c.patch(f"/api/reporting/reports/{rid}/", {"title": "R2"}, format="json").status_code == 200
    assert c.delete(f"/api/reporting/reports/{rid}/").status_code in (200, 204)
    # CJ's report designs are out of his reach.
    assert c.get(f"/api/reporting/reports/{world['cj']['rep'].id}/").status_code == 404


# ---------------------------------------------------------------------------
# #47 — private courses; #52 members learn them
# ---------------------------------------------------------------------------


def test_exclusive_admin_builds_courses_his_members_learn(world):
    org_a = world["org_a"]
    c = _auth(world["u"]["excl_a"])
    resp = c.post("/api/training/courses/", {"title": "Onboarding"}, format="json")
    assert resp.status_code == 201, resp.data
    course = TrainingCourse.objects.get(id=resp.data["data"]["id"])
    assert course.owner_organization_id == org_a.id
    lesson = c.post(f"/api/training/courses/{course.id}/lessons/", {"title": "L1"}, format="json")
    assert lesson.status_code == 201, lesson.data
    assert c.post(f"/api/training/courses/{course.id}/publish/").status_code == 200
    # Edits after publishing need no CJ approval.
    resp = c.patch(f"/api/training/courses/{course.id}/", {"title": "Onboarding 2"}, format="json")
    assert resp.status_code == 200, resp.data

    # He assigns it to his members through the organization's course page.
    org_courses = _auth(world["u"]["excl_a"]).get(f"/api/organizations/{org_a.id}/courses/")
    assert course.id in {row["id"] for row in _data(org_courses)}
    member = world["u"]["member_a"]
    resp = c.post(
        f"/api/organizations/{org_a.id}/courses/{course.id}/assign/",
        {"user_ids": [member.id]},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert CourseRegistration.objects.filter(course=course, student=member).exists()
    assert course.id in _ids(_auth(member).get("/api/training/courses/"))

    # CJ Admin cannot see, edit or delete it; nor its lessons.
    cja = _auth(world["u"]["cj_admin"])
    assert cja.get(f"/api/training/courses/{course.id}/").status_code == 404
    lesson_id = lesson.data["data"]["id"]
    assert cja.patch(f"/api/training/lessons/{lesson_id}/", {"title": "x"}, format="json").status_code == 404

    assert c.delete(f"/api/training/courses/{course.id}/").status_code in (200, 204)


def test_exclusive_admin_cannot_change_licensed_cj_course(world):
    cj_course = world["cj"]["course"]
    c = _auth(world["u"]["excl_a"])
    assert c.get(f"/api/training/courses/{cj_course.id}/").status_code == 200
    assert c.patch(f"/api/training/courses/{cj_course.id}/", {"title": "x"}, format="json").status_code == 403
    assert c.post(f"/api/training/courses/{cj_course.id}/lessons/", {"title": "x"}, format="json").status_code == 403
    assert c.delete(f"/api/training/courses/{cj_course.id}/").status_code == 403
    assert c.post("/api/training/categories/", {"name": "Mine"}, format="json").status_code == 403
