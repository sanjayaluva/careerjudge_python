"""Report 9 (1 Oct 2026): organization managers are limited to their own
organization, cannot escalate roles, and reports/sessions are scoped.

Rights come from the real role table (apps.accounts.role_rights) so these
tests exercise exactly what production roles hold.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment, AssessmentSession
from apps.organizations.models import (
    AssessmentSchedule,
    Group,
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)
from apps.reporting.models import GeneratedReport, Report

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


def _user(roles, role, email):
    return User.objects.create_user(email=email, password="pw", is_active=True, role=roles[role])


def _data(resp):
    body = resp.data.get("data", resp.data)
    return body["results"] if isinstance(body, dict) and "results" in body else body


@pytest.fixture
def world(roles):
    own = Organization.objects.create(name="Own Corp", type="corporate")
    other = Organization.objects.create(name="Other Corp", type="corporate")
    manager = _user(roles, "corp_admin", "mgr@t.com")
    OrganizationMember.objects.create(organization=own, user=manager, is_admin=True)
    emp = _user(roles, "individual", "emp@t.com")
    OrganizationMember.objects.create(organization=own, user=emp)
    stranger = _user(roles, "individual", "stranger@t.com")
    OrganizationMember.objects.create(organization=other, user=stranger)
    cj = _user(roles, "cj_admin", "cj@t.com")
    return {
        "own": own,
        "other": other,
        "manager": manager,
        "emp": emp,
        "stranger": stranger,
        "cj": cj,
    }


# --- organizations --------------------------------------------------------


def test_manager_sees_only_own_organization(world):
    resp = _auth(world["manager"]).get("/api/organizations/")
    assert resp.status_code == 200
    assert {o["id"] for o in _data(resp)} == {world["own"].id}


def test_manager_cannot_reach_other_organization_routes(world):
    c = _auth(world["manager"])
    assert c.get(f"/api/organizations/{world['other'].id}/").status_code == 404
    assert c.get(f"/api/organizations/{world['other'].id}/members/").status_code == 404
    assert c.get(f"/api/organizations/{world['own'].id}/members/").status_code == 200


def test_manager_cannot_create_organization(world):
    resp = _auth(world["manager"]).post("/api/organizations/", {"name": "New"}, format="json")
    assert resp.status_code == 403


def test_only_cj_admin_assigns_content(world):
    a = Assessment.objects.create(title="A", status="published")
    body = {"item_type": "assessment", "item_id": a.id}
    url = f"/api/organizations/{world['own'].id}/assignments/"
    assert _auth(world["manager"]).post(url, body, format="json").status_code == 403
    assert _auth(world["cj"]).post(url, body, format="json").status_code == 201


def test_manager_schedules_only_assigned_assessments_and_can_reschedule(world):
    assigned = Assessment.objects.create(title="Assigned", status="published")
    unassigned = Assessment.objects.create(title="Not assigned", status="published")
    OrganizationAssignment.objects.create(
        organization=world["own"], item_type="assessment", item_id=assigned.id
    )
    c = _auth(world["manager"])
    url = f"/api/organizations/{world['own'].id}/schedules/"
    when = (timezone.now() + timezone.timedelta(days=2)).isoformat()
    refused = c.post(url, {"assessment": unassigned.id, "scheduled_at": when}, format="json")
    assert refused.status_code == 403
    created = c.post(url, {"assessment": assigned.id, "scheduled_at": when}, format="json")
    assert created.status_code == 201, created.data
    sid = created.data["data"]["id"]
    later = (timezone.now() + timezone.timedelta(days=5)).replace(microsecond=0)
    moved = c.patch(f"{url}{sid}/", {"scheduled_at": later.isoformat()}, format="json")
    assert moved.status_code == 200, moved.data
    assert AssessmentSchedule.objects.get(id=sid).scheduled_at == later


def test_manager_sees_only_assigned_published_assessments(world):
    assigned = Assessment.objects.create(title="Assigned", status="published")
    Assessment.objects.create(title="Other", status="published")
    Assessment.objects.create(title="Draft", status="draft")
    OrganizationAssignment.objects.create(
        organization=world["own"], item_type="assessment", item_id=assigned.id
    )
    resp = _auth(world["manager"]).get("/api/assessments/")
    assert {a["id"] for a in _data(resp)} == {assigned.id}


# --- users & roles --------------------------------------------------------


def test_manager_user_list_is_own_members_only(world):
    resp = _auth(world["manager"]).get("/api/accounts/users/")
    ids = {u["id"] for u in _data(resp)}
    assert world["emp"].id in ids
    assert world["stranger"].id not in ids
    assert world["cj"].id not in ids


def test_manager_cannot_assign_roles_or_manage_roles(world, roles):
    c = _auth(world["manager"])
    resp = c.post(
        f"/api/accounts/users/{world['manager'].id}/assign-role/",
        {"role_name": "cj_admin"},
        format="json",
    )
    assert resp.status_code == 403
    world["manager"].refresh_from_db()
    assert world["manager"].role.name == "corp_admin"
    assert c.get("/api/accounts/roles/").status_code == 403


def test_manager_creates_only_allowed_roles_linked_to_his_org(world, roles):
    c = _auth(world["manager"])
    bad = c.post(
        "/api/accounts/users/",
        {"email": "x@t.com", "full_name": "X", "role": roles["cj_admin"].id},
        format="json",
    )
    assert bad.status_code == 400
    ok = c.post(
        "/api/accounts/users/",
        {"email": "y@t.com", "full_name": "Y", "role": roles["individual"].id},
        format="json",
    )
    assert ok.status_code == 201, ok.data
    assert OrganizationMember.objects.filter(
        organization=world["own"], user__email="y@t.com"
    ).exists()


def test_manager_without_organization_cannot_add_users(roles):
    loner = _user(roles, "channel_partner", "cp@t.com")
    resp = _auth(loner).post(
        "/api/accounts/users/",
        {"email": "z@t.com", "full_name": "Z", "role": roles["individual"].id},
        format="json",
    )
    assert resp.status_code == 403


def test_user_created_with_password_still_gets_verification_email(world, roles, mailoutbox):
    resp = _auth(world["manager"]).post(
        "/api/accounts/users/",
        {
            "email": "pw@t.com",
            "full_name": "PW",
            "role": roles["individual"].id,
            "password": "Str0ng!Passw0rd",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["invite_email_sent"] is True
    assert any("pw@t.com" in m.to for m in mailoutbox)


def test_group_admin_limited_to_his_group(world, roles):
    g1 = Group.objects.create(organization=world["own"], name="G1")
    g2 = Group.objects.create(organization=world["own"], name="G2")
    ga = _user(roles, "group_admin", "ga@t.com")
    OrganizationMember.objects.create(organization=world["own"], user=ga, group=g1, is_admin=True)
    OrganizationMember.objects.filter(user=world["emp"]).update(group=g2)
    mate = _user(roles, "individual", "mate@t.com")
    OrganizationMember.objects.create(organization=world["own"], user=mate, group=g1)
    resp = _auth(ga).get(f"/api/organizations/{world['own'].id}/members/")
    emails = {m["user"]["email"] for m in _data(resp)}
    assert "mate@t.com" in emails
    assert "emp@t.com" not in emails


# --- reports & counselling -----------------------------------------------


def _generated(candidate):
    a = Assessment.objects.create(title=f"A-{candidate.id}", status="published")
    s = AssessmentSession.objects.create(assessment=a, candidate=candidate, status="completed")
    return GeneratedReport.objects.create(
        report=Report.objects.create(title="R"), session=s, candidate=candidate, status="generated"
    )


def test_individual_sees_only_own_generated_reports(world):
    mine = _generated(world["emp"])
    _generated(world["stranger"])
    resp = _auth(world["emp"]).get("/api/reporting/generated/")
    assert {r["id"] for r in _data(resp)} == {mine.id}


def test_channel_partner_and_counsellor_have_no_report_access(roles):
    for role in ("channel_partner", "counsellor"):
        u = _user(roles, role, f"{role}@t.com")
        assert _auth(u).get("/api/reporting/generated/").status_code == 403


def test_cannot_generate_report_for_someone_elses_session(world):
    report = Report.objects.create(title="R", status="published")
    a = Assessment.objects.create(title="A", status="published")
    s = AssessmentSession.objects.create(
        assessment=a, candidate=world["stranger"], status="completed"
    )
    resp = _auth(world["emp"]).post(
        f"/api/reporting/reports/{report.id}/generate/", {"session_id": s.id}, format="json"
    )
    assert resp.status_code == 404


def test_manager_cannot_pull_staff_or_other_org_users_into_his_org(world):
    c = _auth(world["manager"])
    url = f"/api/organizations/{world['own'].id}/members/"
    assert c.post(url, {"user_email": "cj@t.com"}, format="json").status_code == 403
    assert c.post(url, {"user_email": "stranger@t.com"}, format="json").status_code == 403


def test_group_admin_cannot_change_groups_or_org(world, roles):
    ga = _user(roles, "group_admin", "ga2@t.com")
    OrganizationMember.objects.create(organization=world["own"], user=ga, is_admin=True)
    c = _auth(ga)
    assert (
        c.post(
            f"/api/organizations/{world['own'].id}/groups/", {"name": "X"}, format="json"
        ).status_code
        == 403
    )
    assert (
        c.patch(
            f"/api/organizations/{world['own'].id}/", {"name": "Renamed"}, format="json"
        ).status_code
        == 403
    )


def test_psychometrician_can_create_profiling_solution_and_report(roles):
    psych = _user(roles, "psychometrician", "psy@t.com")
    c = _auth(psych)
    sol = c.post("/api/career-profiling/solutions/", {"title": "Careers"}, format="json")
    assert sol.status_code in (200, 201), sol.data
    rep = c.post("/api/reporting/reports/", {"title": "General"}, format="json")
    assert rep.status_code in (200, 201), rep.data


def test_cj_admin_switches_modules_off_for_an_organization(world):
    """Report 9 #96: CJ Admin chooses the modules an organization may use;
    its admins and members lose the others (server + /api/me)."""
    c = _auth(world["cj"])
    bad = c.patch(
        f"/api/organizations/{world['own'].id}/", {"enabled_modules": ["nope"]}, format="json"
    )
    assert bad.status_code == 400
    ok = c.patch(
        f"/api/organizations/{world['own'].id}/",
        {"enabled_modules": ["assessment"]},
        format="json",
    )
    assert ok.status_code == 200, ok.data
    emp = _auth(world["emp"])
    assert emp.get("/api/reporting/generated/").status_code == 403
    assert emp.get("/api/assessments/").status_code == 200
    me = emp.get("/api/me/").data["data"]
    assert "reporting" in me["disabled_modules"]
    assert all(r["module"] != "reporting" for r in me["module_rights"])
    # A user outside the organization is unaffected.
    assert _auth(world["stranger"]).get("/api/reporting/generated/").status_code == 200
    # Managers cannot change the switch themselves.
    assert (
        _auth(world["manager"])
        .patch(f"/api/organizations/{world['own'].id}/", {"enabled_modules": None}, format="json")
        .status_code
        == 403
    )


def test_helpdesk_views_everything_read_only(world, roles):
    """Report 9 #112-#114: Help Desk views every organization, assessment
    (any status) and profiling solution, but cannot change or take them."""
    from apps.career_profiling.models import ProfilingSolution

    hd = _user(roles, "helpdesk", "hd@t.com")
    c = _auth(hd)
    draft = Assessment.objects.create(title="Draft", status="draft")
    pub = Assessment.objects.create(title="Pub", status="published")
    sol = ProfilingSolution.objects.create(title="Draft solution", status="draft")

    orgs = {o["id"] for o in _data(c.get("/api/organizations/"))}
    assert {world["own"].id, world["other"].id} <= orgs
    assessments = {a["id"] for a in _data(c.get("/api/assessments/"))}
    assert {draft.id, pub.id} <= assessments
    sols = {s["id"] for s in _data(c.get("/api/career-profiling/solutions/"))}
    assert sol.id in sols

    assert (
        c.patch(f"/api/organizations/{world['own'].id}/", {"name": "X"}, format="json").status_code
        == 403
    )
    assert c.post("/api/assessments/", {"title": "New"}, format="json").status_code == 403
    assert c.post(f"/api/assessments/{pub.id}/start_session/").status_code == 403
    assert (
        c.post("/api/career-profiling/solutions/", {"title": "S"}, format="json").status_code == 403
    )
