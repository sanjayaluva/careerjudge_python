"""Rights audit of 3 Oct 2026 (approved by the client that day).

Every built-in role logs in with the rights of the REAL table
(``sync_role_rights`` + ``get_or_create_default_roles``) and each probe
asserts the behaviour the client's documents require — Report 9 (1 Oct 2026)
first, then Report 4 (13 Aug 2026), the signed User Details and Docs 1-9.

Covers: the table changes (migration 0017), the ``destroy`` guard for
organization managers, the view-level gaps V1-V10 of the audit report, and
the decisions 3a-3f (Group Admin add-only, Help Desk invoices, profiling
request flow, trainer draft deletes, solution licensing, live chat).
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User, UserProfile
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment
from apps.career_profiling.models import ProfilingSolution, ProfilingSolutionModificationRequest
from apps.counseling.models import (
    CounselingCategory,
    CounselingSession,
    CounsellorProfile,
    TimeSlot,
)
from apps.organizations.models import (
    Group,
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)
from apps.question_bank.models import Category, Question, QuestionBankDeletionRequest
from apps.reporting.models import Report
from apps.training.models import TrainingCourse

pytestmark = pytest.mark.django_db

ROLES = [
    "cj_admin",
    "helpdesk",
    "corp_admin",
    "corp_exclusive",
    "psychometrician",
    "sme",
    "reviewer",
    "trainer",
    "group_admin",
    "counsellor",
    "channel_partner",
    "individual",
]

REGISTRATION_FORM = {
    "form": {
        "first_name": "A",
        "last_name": "B",
        "gender": "male",
        "mobile": "1",
        "state_province": "S",
        "city": "C",
        "occupation": "O",
        "highest_education": "H",
        "work_experience": "0",
        "institution_name": "I",
        "place_of_institution": "P",
    }
}


def _auth(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


def _rows(resp):
    body = resp.data.get("data", resp.data)
    return body["results"] if isinstance(body, dict) and "results" in body else body


@pytest.fixture
def W():
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)

    def mk(role, email):
        return User.objects.create_user(
            email=email, password="pw", is_active=True, role=roles[role], full_name=email
        )

    u = {r: mk(r, f"{r}@t.com") for r in ROLES}
    u["emp"] = mk("individual", "emp@t.com")  # corporate employee
    u["pu"] = mk("individual", "pu@t.com")  # channel-partner user
    u["eu"] = mk("individual", "eu@t.com")  # exclusive employee
    u["stranger"] = mk("individual", "stranger@t.com")  # another organization's user
    u["counsellor2"] = mk("counsellor", "counsellor2@t.com")

    corp = Organization.objects.create(name="Corp", type="corporate")
    g1 = Group.objects.create(organization=corp, name="G1")
    OrganizationMember.objects.create(organization=corp, user=u["corp_admin"], is_admin=True)
    OrganizationMember.objects.create(
        organization=corp, user=u["group_admin"], group=g1, can_view_member_reports=True
    )
    m_emp = OrganizationMember.objects.create(organization=corp, user=u["emp"], group=g1)
    cp_org = Organization.objects.create(name="Partner", type="channel_partner")
    OrganizationMember.objects.create(organization=cp_org, user=u["channel_partner"], is_admin=True)
    OrganizationMember.objects.create(organization=cp_org, user=u["pu"])
    ex_org = Organization.objects.create(name="Excl", type="corp_exclusive")
    OrganizationMember.objects.create(organization=ex_org, user=u["corp_exclusive"], is_admin=True)
    OrganizationMember.objects.create(organization=ex_org, user=u["eu"])
    other = Organization.objects.create(name="Other", type="corporate")
    OrganizationMember.objects.create(organization=other, user=u["stranger"])

    a_free = Assessment.objects.create(
        title="Free CJ", status="published", created_by=u["cj_admin"]
    )
    a_other = Assessment.objects.create(
        title="Unlicensed", status="published", created_by=u["cj_admin"]
    )
    for org in (corp, cp_org, ex_org):
        OrganizationAssignment.objects.create(
            organization=org, item_type="assessment", item_id=a_free.id
        )
        OrganizationAssignment.objects.create(organization=org, item_type="counseling", item_id=0)

    cat = Category.objects.create(name="Root", created_by=u["cj_admin"])
    q_defaults = {
        "question_type": "MCQ_TEXT_IMAGE",
        "question_title": "T",
        "question_text_1": "Q?",
        "scoring_type": "BINARY",
    }
    q_sme_draft = Question.objects.create(
        category=cat, created_by=u["sme"], status="draft", **q_defaults
    )
    q_trainer_draft = Question.objects.create(
        category=cat, created_by=u["trainer"], status="draft", **q_defaults
    )
    q_trainer_pub = Question.objects.create(
        category=cat, created_by=u["trainer"], status="confirmed", **q_defaults
    )
    q_pcr = Question.objects.create(
        category=cat,
        created_by=u["sme"],
        status="pending_content_review",
        assigned_reviewer=u["reviewer"],
        **q_defaults,
    )
    q_pcr_other = Question.objects.create(
        category=cat, created_by=u["sme"], status="pending_content_review", **q_defaults
    )
    q_ppr = Question.objects.create(
        category=cat, created_by=u["sme"], status="pending_psychometric_review", **q_defaults
    )

    k_pub = TrainingCourse.objects.create(title="Pub", status="published", created_by=u["trainer"])
    for org in (corp, cp_org, ex_org):
        OrganizationAssignment.objects.create(
            organization=org, item_type="training_course", item_id=k_pub.id
        )

    ccat = CounselingCategory.objects.get_or_create(name="Career")[0]
    up, _ = UserProfile.objects.get_or_create(user=u["counsellor"])
    up.hourly_rate = 0
    up.is_available_for_counseling = True
    up.save()
    prof = CounsellorProfile.objects.create(user=u["counsellor"])
    prof.categories.add(ccat)

    def slot(h):
        start = timezone.now() + timedelta(hours=h)
        return TimeSlot.objects.create(
            counsellor=prof,
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="available",
        )

    s_ind = CounselingSession.objects.create(
        counselee=u["individual"],
        counsellor=prof,
        category=ccat,
        timeslot=slot(48),
        topic="A",
        fee=0,
    )
    return {
        "u": u,
        "corp": corp,
        "g1": g1,
        "m_emp": m_emp,
        "cp_org": cp_org,
        "ex_org": ex_org,
        "a_free": a_free,
        "a_other": a_other,
        "cat": cat,
        "q_sme_draft": q_sme_draft,
        "q_trainer_draft": q_trainer_draft,
        "q_trainer_pub": q_trainer_pub,
        "q_pcr": q_pcr,
        "q_pcr_other": q_pcr_other,
        "q_ppr": q_ppr,
        "k_pub": k_pub,
        "prof": prof,
        "slot": slot,
        "s_ind": s_ind,
    }


# --------------------------------------------------------------------------
# 1. The table itself (migration 0017)
# --------------------------------------------------------------------------


def test_table_changes_of_the_rights_audit():
    rights = {role: set(perms) for role, perms in ROLE_PERMISSIONS.items()}
    assert ("counseling", "change") not in rights["helpdesk"]
    assert ("accounts", "view") not in rights["trainer"]
    assert ("accounts", "view") not in rights["counsellor"]
    assert ("question_bank", "delete") in rights["psychometrician"]
    assert ("career_profiling", "delete") in rights["psychometrician"]
    assert ("question_bank", "delete") in rights["trainer"]
    for role in ("corp_admin", "corp_exclusive", "channel_partner"):
        assert ("accounts", "delete") in rights[role], role
    # 3a: Group Admin adds and bulk-uploads only (Report 9 #23/#24).
    assert rights["group_admin"] & {("accounts", "change"), ("accounts", "delete")} == set()


def test_trainer_and_counsellor_no_longer_list_users(W):
    assert _auth(W["u"]["trainer"]).get("/api/accounts/users/").status_code == 403
    assert _auth(W["u"]["counsellor"]).get("/api/accounts/users/").status_code == 403
    # Their own work is unaffected.
    assert _auth(W["u"]["trainer"]).get("/api/training/courses/").status_code == 200
    assert _auth(W["u"]["counsellor"]).get("/api/counseling/sessions/").status_code == 200


def test_helpdesk_views_sessions_but_cannot_confirm(W):
    hd = _auth(W["u"]["helpdesk"])
    assert hd.get("/api/counseling/sessions/").status_code == 200
    assert hd.post(f"/api/counseling/sessions/{W['s_ind'].id}/confirm/").status_code == 403


def test_psychometrician_delete_only_files_requests(W):
    p = _auth(W["u"]["psychometrician"])
    r = p.delete(
        f"/api/question-bank/questions/{W['q_sme_draft'].id}/", {"reason": "dup"}, format="json"
    )
    assert r.status_code == 201 and "request" in r.data["message"].lower()
    assert Question.objects.filter(id=W["q_sme_draft"].id).exists()
    r = p.delete(f"/api/question-bank/categories/{W['cat'].id}/", {"reason": "dup"}, format="json")
    assert r.status_code == 201
    assert Category.objects.filter(id=W["cat"].id).exists()
    assert (
        QuestionBankDeletionRequest.objects.filter(requester=W["u"]["psychometrician"]).count() == 2
    )


# --------------------------------------------------------------------------
# 2. accounts.delete for organization managers + the destroy guard
# --------------------------------------------------------------------------


def test_managers_delete_only_their_own_members(W):
    u = W["u"]
    ca = _auth(u["corp_admin"])
    assert ca.delete(f"/api/accounts/users/{u['stranger'].id}/").status_code == 404
    assert ca.delete(f"/api/accounts/users/{u['corp_exclusive'].id}/").status_code == 404
    # Never himself, never another manager / staff member of his organization.
    assert ca.delete(f"/api/accounts/users/{u['corp_admin'].id}/").status_code == 403
    OrganizationMember.objects.create(organization=W["corp"], user=u["helpdesk"])
    assert ca.delete(f"/api/accounts/users/{u['helpdesk'].id}/").status_code == 403
    assert User.objects.filter(id=u["helpdesk"].id).exists()
    # His Group Admin (Report 4 CA-4) and his members: yes.
    assert ca.delete(f"/api/accounts/users/{u['group_admin'].id}/").status_code == 200
    assert ca.delete(f"/api/accounts/users/{u['emp'].id}/").status_code == 200
    assert not User.objects.filter(id=u["emp"].id).exists()

    cp = _auth(u["channel_partner"])
    assert cp.delete(f"/api/accounts/users/{u['stranger'].id}/").status_code == 404
    assert cp.delete(f"/api/accounts/users/{u['channel_partner'].id}/").status_code == 403
    assert cp.delete(f"/api/accounts/users/{u['pu'].id}/").status_code == 200

    ce = _auth(u["corp_exclusive"])
    assert ce.delete(f"/api/accounts/users/{u['stranger'].id}/").status_code == 404
    assert ce.delete(f"/api/accounts/users/{u['corp_exclusive'].id}/").status_code == 403
    assert ce.delete(f"/api/accounts/users/{u['eu'].id}/").status_code == 200


def test_group_admin_adds_but_never_edits_or_deletes_users(W):
    ga = _auth(W["u"]["group_admin"])
    individual = Role.objects.get(name="individual").id
    r = ga.post(
        "/api/accounts/users/",
        {"email": "gnew@t.com", "full_name": "N", "role": individual},
        format="json",
    )
    assert r.status_code == 201
    assert (
        ga.patch(
            f"/api/accounts/users/{W['u']['emp'].id}/", {"full_name": "X"}, format="json"
        ).status_code
        == 403
    )
    assert ga.delete(f"/api/accounts/users/{W['u']['emp'].id}/").status_code == 403
    assert User.objects.filter(id=W["u"]["emp"].id).exists()


# --------------------------------------------------------------------------
# 3. View-level gaps V1-V10
# --------------------------------------------------------------------------


def test_v1_managers_do_not_take_assessments(W):
    for role in ("corp_admin", "group_admin", "channel_partner", "corp_exclusive"):
        resp = _auth(W["u"][role]).post(f"/api/assessments/{W['a_free'].id}/start_session/")
        assert resp.status_code == 403, role
    # Members (and plain individuals) still take them (Report 9 #51).
    assert (
        _auth(W["u"]["emp"]).post(f"/api/assessments/{W['a_free'].id}/start_session/").status_code
        == 201
    )
    assert (
        _auth(W["u"]["individual"])
        .post(f"/api/assessments/{W['a_free'].id}/start_session/")
        .status_code
        == 201
    )


def test_v2_only_cj_admin_and_psychometrician_create_categories(W):
    for role in ("sme", "trainer", "reviewer"):
        resp = _auth(W["u"][role]).post(
            "/api/question-bank/categories/", {"name": f"By {role}"}, format="json"
        )
        assert resp.status_code == 403, role
    assert (
        _auth(W["u"]["psychometrician"])
        .post("/api/question-bank/categories/", {"name": "P"}, format="json")
        .status_code
        == 201
    )
    assert (
        _auth(W["u"]["cj_admin"])
        .post("/api/question-bank/categories/", {"name": "A"}, format="json")
        .status_code
        == 201
    )
    # Report 9 #39: the exclusive admin keeps his private categories.
    assert (
        _auth(W["u"]["corp_exclusive"])
        .post("/api/question-bank/categories/", {"name": "Priv"}, format="json")
        .status_code
        == 201
    )


def test_v3_review_type_matches_role(W):
    body = {"action": "approve", "comment": "ok", "rating": 4}
    r = _auth(W["u"]["reviewer"])
    p = _auth(W["u"]["psychometrician"])
    assert (
        r.post(
            f"/api/question-bank/questions/{W['q_ppr'].id}/review/",
            {**body, "review_type": "psychometric"},
            format="json",
        ).status_code
        == 403
    )
    assert (
        p.post(
            f"/api/question-bank/questions/{W['q_pcr'].id}/review/",
            {**body, "review_type": "content"},
            format="json",
        ).status_code
        == 403
    )
    assert r.post(
        f"/api/question-bank/questions/{W['q_pcr'].id}/review/",
        {**body, "review_type": "content"},
        format="json",
    ).status_code in (200, 201)
    assert p.post(
        f"/api/question-bank/questions/{W['q_ppr'].id}/review/",
        {**body, "review_type": "psychometric"},
        format="json",
    ).status_code in (200, 201)


def test_v4_trainer_and_managers_cannot_register_for_courses(W):
    t = _auth(W["u"]["trainer"])
    assert (
        t.post(
            f"/api/training/courses/{W['k_pub'].id}/register/", REGISTRATION_FORM, format="json"
        ).status_code
        == 403
    )
    assert (
        _auth(W["u"]["corp_exclusive"])
        .post(f"/api/training/courses/{W['k_pub'].id}/register/", REGISTRATION_FORM, format="json")
        .status_code
        == 403
    )
    assert _auth(W["u"]["individual"]).post(
        f"/api/training/courses/{W['k_pub'].id}/register/", REGISTRATION_FORM, format="json"
    ).status_code in (200, 201)


def test_v5_counsellor_does_not_book_sessions(W):
    body = {
        "counsellor": W["prof"].id,
        "timeslot": W["slot"](200).id,
        "topic": "self",
        "terms_accepted": True,
    }
    assert (
        _auth(W["u"]["counsellor"])
        .post("/api/counseling/sessions/", body, format="json")
        .status_code
        == 403
    )
    # His own profile / timeslots still work.
    assert (
        _auth(W["u"]["counsellor"])
        .post(
            "/api/counseling/timeslots/",
            {
                "counsellor": W["prof"].id,
                "start_time": (timezone.now() + timedelta(days=5)).isoformat(),
                "end_time": (timezone.now() + timedelta(days=5, hours=1)).isoformat(),
            },
            format="json",
        )
        .status_code
        == 201
    )


def test_v6_learners_do_not_create_courses(W):
    assert (
        _auth(W["u"]["individual"])
        .post("/api/training/courses/", {"title": "By learner"}, format="json")
        .status_code
        == 403
    )
    assert (
        _auth(W["u"]["trainer"])
        .post("/api/training/courses/", {"title": "By trainer"}, format="json")
        .status_code
        == 201
    )
    assert (
        _auth(W["u"]["corp_exclusive"])
        .post("/api/training/courses/", {"title": "Private"}, format="json")
        .status_code
        == 201
    )


def test_v7_only_counsellors_create_counsellor_profiles(W):
    assert (
        _auth(W["u"]["individual"])
        .post("/api/counseling/counsellors/", {}, format="json")
        .status_code
        == 403
    )
    assert not CounsellorProfile.objects.filter(user=W["u"]["individual"]).exists()
    assert (
        _auth(W["u"]["counsellor2"])
        .post("/api/counseling/counsellors/", {}, format="json")
        .status_code
        == 201
    )


def test_v8_only_the_counsellor_or_cj_admin_confirms(W):
    sid = W["s_ind"].id
    assert (
        _auth(W["u"]["individual"]).post(f"/api/counseling/sessions/{sid}/confirm/").status_code
        == 403
    )
    assert (
        _auth(W["u"]["counsellor"]).post(f"/api/counseling/sessions/{sid}/confirm/").status_code
        == 200
    )


def test_v9_reviewer_sees_only_questions_assigned_to_him(W):
    r = _auth(W["u"]["reviewer"])
    ids = {q["id"] for q in _rows(r.get("/api/question-bank/questions/"))}
    assert ids == {W["q_pcr"].id}
    assert r.get(f"/api/question-bank/questions/{W['q_pcr_other'].id}/").status_code == 404


def test_v10_managers_see_only_relevant_report_designs(W):
    cj = W["u"]["cj_admin"]
    rel = Report.objects.create(title="Licensed design", assessment=W["a_free"], created_by=cj)
    Report.objects.create(title="Other design", assessment=W["a_other"], created_by=cj)
    Report.objects.create(title="Unlinked design", created_by=cj)
    for role in ("corp_admin", "group_admin"):
        titles = {d["title"] for d in _rows(_auth(W["u"][role]).get("/api/reporting/reports/"))}
        assert titles == {rel.title}, role
    # Report 4 §3: the exclusive admin never sees CJ's report designs — only
    # his organization's private ones (Report 9 #43).
    Report.objects.create(
        title="Private design", created_by=W["u"]["corp_exclusive"], owner_organization=W["ex_org"]
    )
    titles = {
        d["title"] for d in _rows(_auth(W["u"]["corp_exclusive"]).get("/api/reporting/reports/"))
    }
    assert titles == {"Private design"}
    # The designers still see every CJ design.
    assert len(_rows(_auth(cj).get("/api/reporting/reports/"))) == 3


# --------------------------------------------------------------------------
# 4. Decisions 3b-3f
# --------------------------------------------------------------------------


def test_3b_helpdesk_raises_no_invoices(W):
    hd = _auth(W["u"]["helpdesk"])
    assert hd.post("/api/invoicing/invoices/", {"title": "x"}, format="json").status_code == 403


def test_3d_trainer_deletes_own_draft_questions_only(W):
    t = _auth(W["u"]["trainer"])
    assert (
        t.delete(
            f"/api/question-bank/questions/{W['q_trainer_pub'].id}/", {"reason": "x"}, format="json"
        ).status_code
        == 403
    )
    assert (
        t.delete(
            f"/api/question-bank/questions/{W['q_sme_draft'].id}/", {"reason": "x"}, format="json"
        ).status_code
        == 404
    )
    assert t.delete(f"/api/question-bank/questions/{W['q_trainer_draft'].id}/").status_code == 200
    assert not Question.objects.filter(id=W["q_trainer_draft"].id).exists()
    assert not QuestionBankDeletionRequest.objects.filter(requester=W["u"]["trainer"]).exists()


def test_3e_profiling_solutions_are_licensed_to_organizations(W):
    cj = _auth(W["u"]["cj_admin"])
    pub = ProfilingSolution.objects.create(title="Licensed S", status="published")
    other = ProfilingSolution.objects.create(title="Other S", status="published")
    draft = ProfilingSolution.objects.create(title="Draft S", status="draft")
    url = f"/api/organizations/{W['corp'].id}/assignments/"
    # Only published solutions can be licensed, by CJ Admin only.
    assert (
        cj.post(
            url, {"item_type": "profiling_solution", "item_id": draft.id}, format="json"
        ).status_code
        == 400
    )
    assert (
        _auth(W["u"]["corp_admin"])
        .post(url, {"item_type": "profiling_solution", "item_id": pub.id}, format="json")
        .status_code
        == 403
    )
    r = cj.post(url, {"item_type": "profiling_solution", "item_id": pub.id}, format="json")
    assert r.status_code == 201 and r.data["data"]["item_title"] == "Licensed S"
    # Managers see it listed on their organization page; members see only
    # the licensed solution in Career Profiling; plain individuals see all.
    rows = _rows(_auth(W["u"]["corp_admin"]).get(url))
    assert {a["item_title"] for a in rows if a["item_type"] == "profiling_solution"} == {
        "Licensed S"
    }
    emp = _auth(W["u"]["emp"])
    assert {s["title"] for s in _rows(emp.get("/api/career-profiling/solutions/"))} == {
        "Licensed S"
    }
    assert emp.get(f"/api/career-profiling/solutions/{other.id}/").status_code == 404
    assert {
        s["title"]
        for s in _rows(_auth(W["u"]["individual"]).get("/api/career-profiling/solutions/"))
    } == {
        "Licensed S",
        "Other S",
    }
    # V10: a profiling report design on the licensed solution is relevant.
    Report.objects.create(
        title="Profile design",
        scope="profiling",
        profiling_solution=pub,
        created_by=W["u"]["cj_admin"],
    )
    Report.objects.create(
        title="Other profile design",
        scope="profiling",
        profiling_solution=other,
        created_by=W["u"]["cj_admin"],
    )
    titles = {d["title"] for d in _rows(_auth(W["u"]["corp_admin"]).get("/api/reporting/reports/"))}
    assert titles == {"Profile design"}


def test_3c_psychometrician_profiling_requests_are_approved_by_cj_admin(W):
    p = _auth(W["u"]["psychometrician"])
    cj = _auth(W["u"]["cj_admin"])
    draft = ProfilingSolution.objects.create(
        title="Draft S", status="draft", created_by=W["u"]["psychometrician"]
    )
    pub = ProfilingSolution.objects.create(
        title="Pub S", status="published", created_by=W["u"]["psychometrician"]
    )
    base = "/api/career-profiling/solutions"
    # Delete never happens directly: a reason is required and a request filed.
    assert p.delete(f"{base}/{draft.id}/").status_code == 400
    r = p.delete(f"{base}/{draft.id}/", {"reason": "obsolete"}, format="json")
    assert r.status_code == 201 and r.data["data"]["action"] == "delete"
    assert ProfilingSolution.objects.filter(id=draft.id).exists()
    # A published solution's title change is a request; other edits refused.
    assert p.patch(f"{base}/{pub.id}/", {"purpose": "x"}, format="json").status_code == 403
    r = p.patch(f"{base}/{pub.id}/", {"title": "Renamed", "reason": "typo"}, format="json")
    assert r.status_code == 201 and r.data["data"]["action"] == "edit"
    assert ProfilingSolution.objects.get(id=pub.id).title == "Pub S"
    # Drafts are still edited directly.
    assert p.patch(f"{base}/{draft.id}/", {"purpose": "x"}, format="json").status_code == 200
    # Direct creation of requests is blocked; the psychometrician lists only his own.
    assert (
        p.post("/api/career-profiling/modification-requests/", {}, format="json").status_code == 405
    )
    assert len(_rows(p.get("/api/career-profiling/modification-requests/"))) == 2
    assert (
        _auth(W["u"]["individual"]).get("/api/career-profiling/modification-requests/").status_code
        == 200
    )
    assert (
        _rows(_auth(W["u"]["individual"]).get("/api/career-profiling/modification-requests/")) == []
    )
    reqs = {x.action: x for x in ProfilingSolutionModificationRequest.objects.all()}
    # Only CJ Admin reviews.
    assert (
        p.post(
            f"/api/career-profiling/modification-requests/{reqs['delete'].id}/approve/"
        ).status_code
        == 403
    )
    assert (
        cj.post(
            f"/api/career-profiling/modification-requests/{reqs['edit'].id}/approve/"
        ).status_code
        == 200
    )
    assert ProfilingSolution.objects.get(id=pub.id).title == "Renamed"
    assert (
        cj.post(
            f"/api/career-profiling/modification-requests/{reqs['delete'].id}/decline/",
            {"admin_note": "keep"},
            format="json",
        ).status_code
        == 200
    )
    assert ProfilingSolution.objects.filter(id=draft.id).exists()
    assert (
        cj.post(
            f"/api/career-profiling/modification-requests/{reqs['delete'].id}/approve/"
        ).status_code
        == 400
    )
    # CJ Admin deletes directly.
    assert cj.delete(f"{base}/{draft.id}/").status_code == 200
    assert not ProfilingSolution.objects.filter(id=draft.id).exists()


def test_cj_admin_edits_and_deletes_solutions_directly(W):
    cj = _auth(W["u"]["cj_admin"])
    pub = ProfilingSolution.objects.create(title="Pub S", status="published")
    assert (
        cj.patch(
            f"/api/career-profiling/solutions/{pub.id}/", {"title": "New"}, format="json"
        ).status_code
        == 200
    )
    assert ProfilingSolution.objects.get(id=pub.id).title == "New"
    assert cj.delete(f"/api/career-profiling/solutions/{pub.id}/").status_code == 200
