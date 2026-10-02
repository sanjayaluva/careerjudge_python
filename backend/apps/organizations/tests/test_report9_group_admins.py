"""Report 9 (1 Oct 2026): Corporate Group Admin set-up and his rights.

#21/#37  Corp Admin / Corp Exclusive Admin (and CJ Admin) define a Group Admin
         for a group — new user + invite, or tag an existing member.
#4/#13/#38  per-Group-Admin "Can view & download members' reports".
#27      a Group Admin sees his group's reports only with that permission.
#23      a Group Admin adds, edits and deletes sub-groups inside his group.
#25      a Group Admin schedules assessments for his group (and sub-groups).
"""

from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment, AssessmentSession
from apps.notifications.models import Notification
from apps.organizations.models import (
    Group,
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)
from apps.organizations.scoping import managed_group_ids
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
    org = Organization.objects.create(name="Acme", type="corporate")
    other_org = Organization.objects.create(name="Other", type="corporate")
    north = Group.objects.create(organization=org, name="North", region_division="North Zone")
    south = Group.objects.create(organization=org, name="South")
    corp = _user(roles, "corp_admin", "corp@t.com")
    OrganizationMember.objects.create(organization=org, user=corp, is_admin=True)
    ga = _user(roles, "group_admin", "ga@t.com")
    ga_member = OrganizationMember.objects.create(
        organization=org, user=ga, group=north, is_admin=True
    )
    north_emp = _user(roles, "individual", "n1@t.com")
    OrganizationMember.objects.create(organization=org, user=north_emp, group=north)
    south_emp = _user(roles, "individual", "s1@t.com")
    OrganizationMember.objects.create(organization=org, user=south_emp, group=south)
    return {
        "org": org,
        "other_org": other_org,
        "north": north,
        "south": south,
        "corp": corp,
        "ga": ga,
        "ga_member": ga_member,
        "north_emp": north_emp,
        "south_emp": south_emp,
    }


def _url(org, suffix=""):
    return f"/api/organizations/{org.id}/{suffix}"


# --- #21 create a Group Admin ------------------------------------------------


def _ga_payload(group, **extra):
    return {
        "full_name": "Gita Admin",
        "email": "gita@acme.com",
        "employee_id": "E-77",
        "group_id": group.id,
        "can_view_member_reports": True,
        **extra,
    }


def test_corp_admin_creates_group_admin_with_invite(world, mailoutbox):
    resp = _auth(world["corp"]).post(
        _url(world["org"], "group-admins/"), _ga_payload(world["north"]), format="json"
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["invite_email_sent"] is True
    user = User.objects.get(email="gita@acme.com")
    assert user.role.name == "group_admin"
    assert user.full_name == "Gita Admin"
    assert user.is_active is False  # activates through the emailed link
    m = OrganizationMember.objects.get(user=user)
    assert (m.organization, m.group, m.employee_id) == (world["org"], world["north"], "E-77")
    assert m.is_admin and m.can_view_member_reports
    assert resp.data["data"]["is_group_admin"] is True
    assert any("gita@acme.com" in mail.to for mail in mailoutbox)


def test_group_admin_invite_failure_is_reported(world):
    with mock.patch(
        "apps.accounts.serializers.send_verification_email", side_effect=OSError("smtp down")
    ):
        resp = _auth(world["corp"]).post(
            _url(world["org"], "group-admins/"), _ga_payload(world["north"]), format="json"
        )
    assert resp.status_code == 201
    assert resp.data["data"]["invite_email_sent"] is False
    assert "could not be sent" in resp.data["message"]


def test_cj_admin_and_corp_exclusive_can_create_group_admins(world, roles):
    cj = _user(roles, "cj_admin", "cj@t.com")
    resp = _auth(cj).post(
        _url(world["org"], "group-admins/"), _ga_payload(world["south"]), format="json"
    )
    assert resp.status_code == 201, resp.data

    excl_org = Organization.objects.create(name="Excl", type="corp_exclusive")
    grp = Group.objects.create(organization=excl_org, name="Ops")
    excl = _user(roles, "corp_exclusive", "excl@t.com")
    OrganizationMember.objects.create(organization=excl_org, user=excl, is_admin=True)
    resp = _auth(excl).post(
        _url(excl_org, "group-admins/"),
        _ga_payload(grp, email="ops@excl.com"),
        format="json",
    )
    assert resp.status_code == 201, resp.data


def test_group_admin_creation_refusals(world, roles):
    url = _url(world["org"], "group-admins/")
    # A Group Admin (or an individual) does not define Group Admins.
    assert (
        _auth(world["ga"]).post(url, _ga_payload(world["north"]), format="json").status_code == 403
    )
    assert (
        _auth(world["north_emp"]).post(url, _ga_payload(world["north"]), format="json").status_code
        == 403
    )
    corp = _auth(world["corp"])
    # Group is required and must belong to this organization.
    assert (
        corp.post(url, _ga_payload(world["north"], group_id=None), format="json").status_code == 400
    )
    foreign = Group.objects.create(organization=world["other_org"], name="X")
    assert corp.post(url, _ga_payload(foreign), format="json").status_code == 400
    # An existing email is not silently re-used.
    assert (
        corp.post(url, _ga_payload(world["north"], email="n1@t.com"), format="json").status_code
        == 400
    )
    # Another organization's page is out of reach.
    assert (
        corp.post(
            _url(world["other_org"], "group-admins/"), _ga_payload(world["north"]), format="json"
        ).status_code
        == 404
    )


# --- #37 tag an existing member as Group Admin --------------------------------


def _member(user):
    return OrganizationMember.objects.get(user=user)


def test_corp_admin_tags_existing_member_as_group_admin_and_back(world):
    m = _member(world["north_emp"])
    url = _url(world["org"], f"members/{m.id}/")
    c = _auth(world["corp"])
    resp = c.patch(url, {"is_group_admin": True, "can_view_member_reports": True}, format="json")
    assert resp.status_code == 200, resp.data
    m.refresh_from_db()
    world["north_emp"].refresh_from_db()
    assert world["north_emp"].role.name == "group_admin"
    assert m.is_admin and m.can_view_member_reports
    assert resp.data["data"]["is_group_admin"] is True

    resp = c.patch(url, {"is_group_admin": False}, format="json")
    assert resp.status_code == 200
    m.refresh_from_db()
    world["north_emp"].refresh_from_db()
    assert world["north_emp"].role.name == "individual"
    assert not m.is_admin and not m.can_view_member_reports


def test_tagging_needs_a_group_and_an_individual(world, roles):
    loose = _user(roles, "individual", "loose@t.com")
    lm = OrganizationMember.objects.create(organization=world["org"], user=loose)
    c = _auth(world["corp"])
    resp = c.patch(_url(world["org"], f"members/{lm.id}/"), {"is_group_admin": True}, format="json")
    assert resp.status_code == 400
    # Group chosen in the same request is fine.
    resp = c.patch(
        _url(world["org"], f"members/{lm.id}/"),
        {"group_id": world["south"].id, "is_group_admin": True},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    # The Corp Admin himself (not an individual) cannot be turned into one.
    corp_m = _member(world["corp"])
    resp = c.patch(
        _url(world["org"], f"members/{corp_m.id}/"),
        {"group_id": world["south"].id, "is_group_admin": True},
        format="json",
    )
    assert resp.status_code == 400


# --- #4/#13/#38 the report permission ---------------------------------------


def test_report_permission_set_and_edited_only_by_org_admin(world):
    url = _url(world["org"], f"members/{world['ga_member'].id}/")
    assert (
        _auth(world["ga"]).patch(url, {"can_view_member_reports": True}, format="json").status_code
        == 403
    )
    c = _auth(world["corp"])
    assert c.patch(url, {"can_view_member_reports": True}, format="json").status_code == 200
    world["ga_member"].refresh_from_db()
    assert world["ga_member"].can_view_member_reports is True
    assert c.patch(url, {"can_view_member_reports": False}, format="json").status_code == 200
    world["ga_member"].refresh_from_db()
    assert world["ga_member"].can_view_member_reports is False
    # Only meaningful for a Group Admin.
    emp = _member(world["north_emp"])
    resp = c.patch(
        _url(world["org"], f"members/{emp.id}/"), {"can_view_member_reports": True}, format="json"
    )
    assert resp.status_code == 400


def test_group_admin_cannot_escalate_or_move_members_out(world):
    c = _auth(world["ga"])
    emp = _member(world["north_emp"])
    url = _url(world["org"], f"members/{emp.id}/")
    assert c.patch(url, {"is_admin": True}, format="json").status_code == 403
    assert c.patch(url, {"is_group_admin": True}, format="json").status_code == 403
    assert c.patch(url, {"group_id": world["south"].id}, format="json").status_code == 403
    assert c.patch(url, {"group_id": None}, format="json").status_code == 403


def test_member_group_must_belong_to_organization(world):
    emp = _member(world["north_emp"])
    foreign = Group.objects.create(organization=world["other_org"], name="F")
    resp = _auth(world["corp"]).patch(
        _url(world["org"], f"members/{emp.id}/"), {"group_id": foreign.id}, format="json"
    )
    assert resp.status_code == 400


# --- #27 report visibility ---------------------------------------------------


def _generated(candidate):
    a = Assessment.objects.create(title=f"A-{candidate.id}", status="published")
    s = AssessmentSession.objects.create(assessment=a, candidate=candidate, status="completed")
    return GeneratedReport.objects.create(
        report=Report.objects.create(title="R"), session=s, candidate=candidate, status="generated"
    )


def test_group_admin_sees_members_reports_only_with_permission(world, roles):
    sub = Group.objects.create(organization=world["org"], name="North-1", parent=world["north"])
    sub_emp = _user(roles, "individual", "sub@t.com")
    OrganizationMember.objects.create(organization=world["org"], user=sub_emp, group=sub)
    north_r = _generated(world["north_emp"])
    sub_r = _generated(sub_emp)
    south_r = _generated(world["south_emp"])
    c = _auth(world["ga"])

    # Permission off: none of the members' reports, in the list or by id.
    assert _data(c.get("/api/reporting/generated/")) == []
    assert c.get(f"/api/reporting/generated/{north_r.id}/").status_code == 404
    access = c.get("/api/organizations/my-access/")
    assert access.status_code == 200
    assert access.data["data"]["can_view_member_reports"] is False

    world["ga_member"].can_view_member_reports = True
    world["ga_member"].save()
    ids = {r["id"] for r in _data(c.get("/api/reporting/generated/"))}
    assert ids == {north_r.id, sub_r.id}
    assert south_r.id not in ids
    assert c.get(f"/api/reporting/generated/{north_r.id}/").status_code == 200
    assert c.get(f"/api/reporting/generated/{south_r.id}/").status_code == 404
    assert c.get("/api/organizations/my-access/").data["data"]["can_view_member_reports"] is True

    # The Corp Admin's own view is unchanged: every member of his organization.
    corp_ids = {r["id"] for r in _data(_auth(world["corp"]).get("/api/reporting/generated/"))}
    assert corp_ids == {north_r.id, sub_r.id, south_r.id}


def test_untagged_group_admin_sees_no_member_reports(world, roles):
    loose_ga = _user(roles, "group_admin", "loose-ga@t.com")
    OrganizationMember.objects.create(
        organization=world["org"], user=loose_ga, is_admin=True, can_view_member_reports=True
    )
    _generated(world["north_emp"])
    assert _data(_auth(loose_ga).get("/api/reporting/generated/")) == []


# --- #23 sub-groups ------------------------------------------------------------


def test_group_admin_manages_sub_groups_within_his_group(world, roles):
    c = _auth(world["ga"])
    groups_url = _url(world["org"], "groups/")
    # Create a sub-group under his group, and a sub-sub-group under that.
    resp = c.post(
        groups_url,
        {"name": "North-1", "region_division": "N1", "parent": world["north"].id},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    sub_id = resp.data["data"]["id"]
    assert resp.data["data"]["parent"] == world["north"].id
    resp = c.post(groups_url, {"name": "North-1a", "parent": sub_id}, format="json")
    assert resp.status_code == 201, resp.data
    subsub_id = resp.data["data"]["id"]

    # His scope now covers the sub-groups.
    assert set(managed_group_ids(world["ga"])) == {world["north"].id, sub_id, subsub_id}
    deep = _user(roles, "individual", "deep@t.com")
    OrganizationMember.objects.create(organization=world["org"], user=deep, group_id=subsub_id)
    emails = {m["user"]["email"] for m in _data(c.get(_url(world["org"], "members/")))}
    assert "deep@t.com" in emails and "s1@t.com" not in emails

    # Group list / organization page show only his group and its sub-groups.
    listed = {g["id"]: g for g in _data(c.get(groups_url))}
    assert set(listed) == {world["north"].id, sub_id, subsub_id}
    assert listed[world["north"].id]["can_manage"] is False
    assert listed[sub_id]["can_manage"] is True
    org_groups = _data(c.get(_url(world["org"])))["groups"]
    assert {g["id"] for g in org_groups} == {world["north"].id, sub_id, subsub_id}

    # Edit and delete a sub-group.
    resp = c.patch(
        f"{groups_url}{sub_id}/", {"name": "North-One", "region_division": "N-1"}, format="json"
    )
    assert resp.status_code == 200, resp.data
    assert Group.objects.get(id=sub_id).name == "North-One"
    assert c.delete(f"{groups_url}{subsub_id}/").status_code == 200
    assert not Group.objects.filter(id=subsub_id).exists()


def test_group_admin_group_changes_refused_outside_his_subtree(world):
    c = _auth(world["ga"])
    groups_url = _url(world["org"], "groups/")
    # No top-level groups, none under another group.
    assert c.post(groups_url, {"name": "Top"}, format="json").status_code == 403
    assert (
        c.post(groups_url, {"name": "S-1", "parent": world["south"].id}, format="json").status_code
        == 403
    )
    # His own group is the Corp Admin's to rename or delete.
    own = f"{groups_url}{world['north'].id}/"
    assert c.patch(own, {"name": "Mine"}, format="json").status_code == 403
    assert c.delete(own).status_code == 403
    # Other groups are out of sight.
    other = f"{groups_url}{world['south'].id}/"
    assert c.patch(other, {"name": "Taken"}, format="json").status_code == 404
    assert c.delete(other).status_code == 404
    # He cannot lift a sub-group out of his group.
    sub = Group.objects.create(organization=world["org"], name="N-x", parent=world["north"])
    resp = c.patch(f"{groups_url}{sub.id}/", {"parent": world["south"].id}, format="json")
    assert resp.status_code == 403
    resp = c.patch(f"{groups_url}{sub.id}/", {"parent": None}, format="json")
    assert resp.status_code == 403
    assert Group.objects.get(id=sub.id).parent_id == world["north"].id


def test_corp_admin_edits_groups_and_cycles_are_refused(world):
    c = _auth(world["corp"])
    groups_url = _url(world["org"], "groups/")
    resp = c.patch(
        f"{groups_url}{world['south'].id}/",
        {"name": "South Zone", "region_division": "S"},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert Group.objects.get(id=world["south"].id).region_division == "S"
    sub = Group.objects.create(organization=world["org"], name="N-x", parent=world["north"])
    resp = c.patch(f"{groups_url}{world['north'].id}/", {"parent": sub.id}, format="json")
    assert resp.status_code == 400
    foreign = Group.objects.create(organization=world["other_org"], name="F")
    resp = c.post(groups_url, {"name": "Bad", "parent": foreign.id}, format="json")
    assert resp.status_code == 400


# --- #25 scheduling for a tagged Group Admin -----------------------------------


def test_group_admin_schedules_assessments_for_his_group(world, roles):
    a = Assessment.objects.create(title="Aptitude", status="published")
    OrganizationAssignment.objects.create(
        organization=world["org"], item_type="assessment", item_id=a.id
    )
    sub = Group.objects.create(organization=world["org"], name="N-1", parent=world["north"])
    sub_emp = _user(roles, "individual", "sub2@t.com")
    OrganizationMember.objects.create(organization=world["org"], user=sub_emp, group=sub)
    c = _auth(world["ga"])
    url = _url(world["org"], "schedules/")
    when = (timezone.now() + timezone.timedelta(days=3)).isoformat()

    resp = c.post(url, {"assessment": a.id, "scheduled_at": when, "group": world["north"].id})
    assert resp.status_code == 201, resp.data
    # His group's members — including the sub-group's — are notified.
    assert Notification.objects.filter(recipient=world["north_emp"]).exists()
    assert Notification.objects.filter(recipient=sub_emp).exists()
    assert not Notification.objects.filter(recipient=world["south_emp"]).exists()

    assert (
        c.post(url, {"assessment": a.id, "scheduled_at": when, "group": sub.id}).status_code == 201
    )
    assert (
        c.post(
            url, {"assessment": a.id, "scheduled_at": when, "group": world["south"].id}
        ).status_code
        == 403
    )
    assert c.post(url, {"assessment": a.id, "scheduled_at": when}).status_code == 403
