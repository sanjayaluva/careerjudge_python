"""Code review (3 Oct 2026) — organization scoping and member management.

#2  a manager cannot add an EXISTING account by email (account takeover);
    the member list shows a slim user record.
#3  a Group Admin with no group reaches nothing (was organization-wide).
#4  member create validates the group and who may set ``is_admin``.
#5  a Group Admin cannot delete admins, Group Admins or himself.
#6  deleting a group deletes its schedules (they no longer widen to all).
#8  licensed-item titles are read in bulk.
#10 the logo of an inactive portal is not served; website ``is_active`` is
    CJ Admin's; ``logo_url`` must be http(s).
    CJ staff tagged to an exclusive organization do not see its private content.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment
from apps.organizations.models import (
    AssessmentSchedule,
    CorporateWebsite,
    CourseSchedule,
    Group,
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)
from apps.organizations.private_content import member_exclusive_org_ids
from apps.organizations.scoping import is_cj_staff, managed_group_ids, managed_user_ids

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
    other = Organization.objects.create(name="Other", type="corporate")
    north = Group.objects.create(organization=org, name="North")
    south = Group.objects.create(organization=org, name="South")
    foreign = Group.objects.create(organization=other, name="Foreign")
    corp = _user(roles, "corp_admin", "corp@t.com")
    OrganizationMember.objects.create(organization=org, user=corp, is_admin=True)
    ga = _user(roles, "group_admin", "ga@t.com")
    ga_member = OrganizationMember.objects.create(
        organization=org, user=ga, group=north, is_admin=True
    )
    ga2 = _user(roles, "group_admin", "ga2@t.com")
    ga2_member = OrganizationMember.objects.create(
        organization=org, user=ga2, group=north, is_admin=True
    )
    north_emp = _user(roles, "individual", "n1@t.com")
    north_emp_member = OrganizationMember.objects.create(
        organization=org, user=north_emp, group=north
    )
    south_emp = _user(roles, "individual", "s1@t.com")
    OrganizationMember.objects.create(organization=org, user=south_emp, group=south)
    return {
        "org": org,
        "other": other,
        "north": north,
        "south": south,
        "foreign": foreign,
        "corp": corp,
        "ga": ga,
        "ga_member": ga_member,
        "ga2_member": ga2_member,
        "north_emp": north_emp,
        "north_emp_member": north_emp_member,
        "south_emp": south_emp,
    }


def _url(org, suffix=""):
    return f"/api/organizations/{org.id}/{suffix}"


# --- #2 account takeover ----------------------------------------------------


@pytest.mark.parametrize("role", ["corp_admin", "corp_exclusive", "channel_partner"])
def test_manager_cannot_add_existing_account_by_email(roles, role):
    org = Organization.objects.create(name="Org", type="corporate")
    manager = _user(roles, role, "m@t.com")
    OrganizationMember.objects.create(organization=org, user=manager, is_admin=True)
    victim = _user(roles, "individual", "victim@gmail.com")

    resp = _auth(manager).post(_url(org, "members/"), {"user_email": "victim@gmail.com"})

    assert resp.status_code == 403
    assert "Only CJ Admin" in str(resp.data)
    assert not OrganizationMember.objects.filter(user=victim).exists()
    assert victim.id not in managed_user_ids(manager)


def test_group_admin_cannot_add_existing_account_by_email(world, roles):
    _user(roles, "individual", "victim@gmail.com")
    resp = _auth(world["ga"]).post(
        _url(world["org"], "members/"), {"user_email": "victim@gmail.com", "full_name": "V"}
    )
    assert resp.status_code == 403


def test_cj_admin_still_adds_existing_account(world, roles):
    cj = _user(roles, "cj_admin", "cj@t.com")
    victim = _user(roles, "individual", "plain@gmail.com")
    resp = _auth(cj).post(_url(world["org"], "members/"), {"user_email": "plain@gmail.com"})
    assert resp.status_code == 201
    assert OrganizationMember.objects.filter(user=victim, organization=world["org"]).exists()


def test_manager_still_creates_new_member(world):
    resp = _auth(world["corp"]).post(
        _url(world["org"], "members/"),
        {"user_email": "new@t.com", "full_name": "New Person", "group_id": world["south"].id},
        format="json",
    )
    assert resp.status_code == 201
    member = OrganizationMember.objects.get(user__email="new@t.com")
    assert member.group_id == world["south"].id


def test_member_list_exposes_slim_user(world):
    profile = world["north_emp"].profile if hasattr(world["north_emp"], "profile") else None
    if profile is None:
        from apps.accounts.models import UserProfile

        profile = UserProfile.objects.create(user=world["north_emp"])
    profile.pan_number = "ABCDE1234F"
    profile.save()
    rows = _data(_auth(world["corp"]).get(_url(world["org"], "members/")))
    user = next(r["user"] for r in rows if r["user"]["email"] == "n1@t.com")
    assert set(user) == {"id", "email", "full_name", "role", "phone", "is_active"}
    assert user["role"] == "individual"
    assert "ABCDE1234F" not in str(rows)


# --- #3 Group Admin without a group -----------------------------------------


def test_group_admin_without_group_reaches_nothing(world):
    ga = world["ga"]
    assert (
        _auth(world["corp"]).delete(_url(world["org"], f"groups/{world['north'].id}/")).status_code
        == 200
    )
    assert OrganizationMember.objects.get(pk=world["ga_member"].pk).group_id is None

    assert managed_group_ids(ga) == []
    assert managed_user_ids(ga) == []
    c = _auth(ga)
    assert _data(c.get(_url(world["org"], "members/"))) == []
    assert {u["email"] for u in _data(c.get("/api/accounts/users/"))} == {"ga@t.com"}
    assert _data(c.get(_url(world["org"], "groups/"))) == []
    assert _data(c.get(_url(world["org"])))["groups"] == []

    a = Assessment.objects.create(title="A", status="published", created_by=world["corp"])
    OrganizationAssignment.objects.create(
        organization=world["org"], item_type="assessment", item_id=a.id, assigned_by=world["corp"]
    )
    resp = c.post(
        _url(world["org"], "schedules/"),
        {"assessment": a.id, "scheduled_at": "2030-01-01T10:00:00Z"},
        format="json",
    )
    assert resp.status_code == 403
    resp = c.post(
        _url(world["org"], "members/"),
        {"user_email": "x@t.com", "full_name": "X", "group_id": world["south"].id},
        format="json",
    )
    assert resp.status_code == 403
    resp = c.post(
        "/api/accounts/users/",
        {"email": "y@t.com", "full_name": "Y", "role": Role.objects.get(name="individual").id},
        format="json",
    )
    assert resp.status_code == 403
    assert not User.objects.filter(email__in=["x@t.com", "y@t.com"]).exists()


def test_group_admin_cannot_lose_his_group(world):
    resp = _auth(world["corp"]).patch(
        _url(world["org"], f"members/{world['ga_member'].id}/"), {"group_id": None}, format="json"
    )
    assert resp.status_code == 400
    assert OrganizationMember.objects.get(pk=world["ga_member"].pk).group_id == world["north"].id


def test_member_update_rejects_non_numeric_group(world):
    resp = _auth(world["corp"]).patch(
        _url(world["org"], f"members/{world['north_emp_member'].id}/"), {"group_id": "abc"}
    )
    assert resp.status_code == 400


# --- #4 member create guards ------------------------------------------------


def test_member_create_rejects_group_of_another_org(world):
    resp = _auth(world["corp"]).post(
        _url(world["org"], "members/"),
        {"user_email": "x@t.com", "full_name": "X", "group_id": world["foreign"].id},
        format="json",
    )
    assert resp.status_code == 400
    assert not User.objects.filter(email="x@t.com").exists()


def test_group_admin_creates_member_only_in_his_subtree(world):
    resp = _auth(world["ga"]).post(
        _url(world["org"], "members/"),
        {"user_email": "x@t.com", "full_name": "X", "group_id": world["south"].id},
        format="json",
    )
    assert resp.status_code == 403
    assert not OrganizationMember.objects.filter(user__email="x@t.com").exists()


def test_group_admin_cannot_create_admin_member(world):
    resp = _auth(world["ga"]).post(
        _url(world["org"], "members/"),
        {"user_email": "x@t.com", "full_name": "X", "is_admin": True},
        format="json",
    )
    assert resp.status_code == 403
    assert not OrganizationMember.objects.filter(user__email="x@t.com").exists()


def test_channel_partner_cannot_create_admin_member(roles):
    org = Organization.objects.create(name="CP Org", type="channel_partner")
    cp = _user(roles, "channel_partner", "cp@t.com")
    OrganizationMember.objects.create(organization=org, user=cp, is_admin=True)
    resp = _auth(cp).post(
        _url(org, "members/"),
        {"user_email": "x@t.com", "full_name": "X", "is_admin": True},
        format="json",
    )
    assert resp.status_code == 403


def test_corp_admin_may_create_admin_member(world):
    resp = _auth(world["corp"]).post(
        _url(world["org"], "members/"),
        {"user_email": "x@t.com", "full_name": "X", "is_admin": True},
        format="json",
    )
    assert resp.status_code == 201
    assert OrganizationMember.objects.get(user__email="x@t.com").is_admin is True


# --- #5 member delete guard -------------------------------------------------


def test_group_admin_cannot_delete_group_admins_or_himself(world):
    c = _auth(world["ga"])
    for member in (world["ga2_member"], world["ga_member"]):
        resp = c.delete(_url(world["org"], f"members/{member.id}/"))
        assert resp.status_code == 403
        assert OrganizationMember.objects.filter(pk=member.pk).exists()
    resp = c.delete(_url(world["org"], f"members/{world['north_emp_member'].id}/"))
    assert resp.status_code == 200


def test_corp_admin_still_deletes_group_admin_membership(world):
    resp = _auth(world["corp"]).delete(_url(world["org"], f"members/{world['ga2_member'].id}/"))
    assert resp.status_code == 200


# --- #6 schedules go with their group -----------------------------------------


def test_deleting_group_deletes_its_schedules(world):
    from apps.training.models import TrainingCourse

    a = Assessment.objects.create(title="A", status="published", created_by=world["corp"])
    course = TrainingCourse.objects.create(title="C", status="published")
    a_sched = AssessmentSchedule.objects.create(
        organization=world["org"],
        group=world["south"],
        assessment=a,
        scheduled_at="2030-01-01T10:00:00Z",
    )
    c_sched = CourseSchedule.objects.create(
        organization=world["org"],
        group=world["south"],
        course=course,
        scheduled_at="2030-01-01T10:00:00Z",
    )
    whole_org = AssessmentSchedule.objects.create(
        organization=world["org"], assessment=a, scheduled_at="2030-01-01T10:00:00Z"
    )
    world["south"].delete()
    assert not AssessmentSchedule.objects.filter(pk=a_sched.pk).exists()
    assert not CourseSchedule.objects.filter(pk=c_sched.pk).exists()
    assert AssessmentSchedule.objects.filter(pk=whole_org.pk).exists()


# --- #8 licensed item titles in bulk ----------------------------------------


def test_assignment_titles_resolved_in_bulk(world, roles):
    cj = _user(roles, "cj_admin", "cj@t.com")
    for i in range(6):
        a = Assessment.objects.create(title=f"A{i}", status="published", created_by=cj)
        OrganizationAssignment.objects.create(
            organization=world["org"], item_type="assessment", item_id=a.id, assigned_by=cj
        )
    OrganizationAssignment.objects.create(
        organization=world["org"], item_type="assessment", item_id=999999, assigned_by=cj
    )
    c = _auth(cj)
    c.get(_url(world["org"], "assignments/"))  # warm-up (auth, rights)
    with CaptureQueriesContext(connection) as few:
        rows = _data(c.get(_url(world["org"], "assignments/")))
    titles = {r["item_title"] for r in rows}
    assert {f"A{i}" for i in range(6)} <= titles and "#999999" in titles
    for i in range(6, 16):
        a = Assessment.objects.create(title=f"A{i}", status="published", created_by=cj)
        OrganizationAssignment.objects.create(
            organization=world["org"], item_type="assessment", item_id=a.id, assigned_by=cj
        )
    with CaptureQueriesContext(connection) as many:
        _data(c.get(_url(world["org"], "assignments/")))
    assert len(many.captured_queries) == len(few.captured_queries)


# --- #10 corporate website ----------------------------------------------------


@pytest.fixture
def website(world, tmp_path, settings):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    site = CorporateWebsite.objects.create(
        organization=world["org"], slug="acme", company_name="Acme"
    )
    site.logo.save("logo.png", SimpleUploadedFile("logo.png", b"\x89PNG data"), save=True)
    return site


def test_inactive_portal_logo_not_served(website):
    assert APIClient().get("/api/organizations/site/acme/logo/").status_code == 200
    website.is_active = False
    website.save()
    assert APIClient().get("/api/organizations/site/acme/logo/").status_code == 404


def test_org_admin_cannot_switch_portal_off(world, website):
    resp = _auth(world["corp"]).patch(
        _url(world["org"], "website/"), {"is_active": False}, format="json"
    )
    assert resp.status_code == 400
    website.refresh_from_db()
    assert website.is_active is True
    # Sending the unchanged value (a full form) is fine.
    resp = _auth(world["corp"]).patch(
        _url(world["org"], "website/"),
        {"is_active": True, "company_name": "Acme Ltd"},
        format="json",
    )
    assert resp.status_code == 200


def test_cj_admin_switches_portal_off(world, website, roles):
    cj = _user(roles, "cj_admin", "cj@t.com")
    resp = _auth(cj).patch(_url(world["org"], "website/"), {"is_active": False}, format="json")
    assert resp.status_code == 200
    website.refresh_from_db()
    assert website.is_active is False


@pytest.mark.parametrize(
    "value", ["javascript:alert(1)", "data:image/png;base64,AAAA", "ftp://x/y.png", "logo.png"]
)
def test_logo_url_must_be_http(world, website, value):
    resp = _auth(world["corp"]).patch(
        _url(world["org"], "website/"), {"logo_url": value}, format="json"
    )
    assert resp.status_code == 400


def test_logo_url_http_accepted(world, website):
    resp = _auth(world["corp"]).patch(
        _url(world["org"], "website/"), {"logo_url": "https://cdn.example.com/l.png"}, format="json"
    )
    assert resp.status_code == 200


# --- CJ staff tagged to an exclusive organization ---------------------------


@pytest.mark.parametrize(
    "role", ["cj_admin", "helpdesk", "psychometrician", "sme", "reviewer", "trainer", "counsellor"]
)
def test_cj_staff_member_of_exclusive_org_sees_no_private_content(roles, role):
    org = Organization.objects.create(name="Excl", type="corp_exclusive")
    staff = _user(roles, role, "staff@t.com")
    OrganizationMember.objects.create(organization=org, user=staff)
    assert is_cj_staff(staff)
    assert member_exclusive_org_ids(staff) == []
    ce = _user(roles, "corp_exclusive", "ce@t.com")
    OrganizationMember.objects.create(organization=org, user=ce, is_admin=True)
    a = Assessment.objects.create(
        title="Private", status="published", created_by=ce, owner_organization=org
    )
    AssessmentSchedule.objects.create(
        organization=org, assessment=a, scheduled_at="2030-01-01T10:00:00Z", created_by=ce
    )
    resp = _auth(staff).get(_url(org, "schedules/"))
    assert resp.status_code in (200, 403, 404)
    if resp.status_code == 200:
        assert _data(resp) == []


def test_exclusive_org_member_still_sees_private_content(roles):
    org = Organization.objects.create(name="Excl", type="corp_exclusive")
    emp = _user(roles, "individual", "emp@t.com")
    OrganizationMember.objects.create(organization=org, user=emp)
    assert not is_cj_staff(emp)
    assert member_exclusive_org_ids(emp) == [org.id]
