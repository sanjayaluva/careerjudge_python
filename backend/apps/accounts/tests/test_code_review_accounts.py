"""Code review (3 Oct 2026) — user management by organization managers.

#2  a manager cannot change a member's email, password or account flags.
#3  a manager cannot give the Group Admin role through the user form.
#7  non-numeric organization / group ids are a 4xx, not a 500.
#8  listing users does not resolve organization modules per row.
#11 the latest role-rights sync migration creates the system roles on a fresh database.
"""

import importlib

import pytest
from django.apps import apps as django_apps
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.organizations.models import Group, Organization, OrganizationMember

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
        email=email, password="Old-pass1!", is_active=True, role=roles[role], **extra
    )


@pytest.fixture
def org_world(roles):
    org = Organization.objects.create(name="Acme", type="corporate")
    north = Group.objects.create(organization=org, name="North")
    corp = _user(roles, "corp_admin", "corp@t.com")
    OrganizationMember.objects.create(organization=org, user=corp, is_admin=True)
    member = _user(roles, "individual", "m@t.com", is_email_verified=True)
    OrganizationMember.objects.create(organization=org, user=member, group=north)
    return {"org": org, "north": north, "corp": corp, "member": member}


# --- #2 ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "Hijacked123!"},
        {"email": "mine@evil.com"},
        {"is_active": False},
        {"is_email_verified": False},
        {"is_trial_user": True},
    ],
)
def test_manager_cannot_change_sign_in_or_account_flags(org_world, payload):
    member = org_world["member"]
    resp = _auth(org_world["corp"]).patch(
        f"/api/accounts/users/{member.id}/", payload, format="json"
    )
    assert resp.status_code == 403
    member.refresh_from_db()
    assert member.check_password("Old-pass1!")
    assert member.email == "m@t.com"
    assert member.is_active and member.is_email_verified and not member.is_trial_user


def test_manager_edits_name_and_phone_with_the_full_form(org_world):
    """The edit form sends every field; unchanged locked values are fine."""
    member = org_world["member"]
    resp = _auth(org_world["corp"]).patch(
        f"/api/accounts/users/{member.id}/",
        {
            "email": "M@t.com",
            "full_name": "New Name",
            "phone": "12345",
            "is_active": True,
            "is_email_verified": True,
            "is_trial_user": False,
            "role": member.role_id,
        },
        format="json",
    )
    assert resp.status_code == 200, resp.data
    member.refresh_from_db()
    assert member.full_name == "New Name" and member.phone == "12345"


def test_cj_admin_still_changes_plain_users_password(roles):
    cj = _user(roles, "cj_admin", "cj@t.com")
    plain = _user(roles, "individual", "plain@t.com")
    resp = _auth(cj).patch(
        f"/api/accounts/users/{plain.id}/", {"password": "Brand-new1!"}, format="json"
    )
    assert resp.status_code == 200
    plain.refresh_from_db()
    assert plain.check_password("Brand-new1!")


# --- #3 ----------------------------------------------------------------------


def test_manager_cannot_create_group_admin_via_user_form(org_world, roles):
    resp = _auth(org_world["corp"]).post(
        "/api/accounts/users/",
        {"email": "g@t.com", "full_name": "G", "role": roles["group_admin"].id},
        format="json",
    )
    assert resp.status_code == 400
    assert not User.objects.filter(email="g@t.com").exists()


def test_manager_cannot_promote_to_group_admin_via_user_form(org_world, roles):
    member = org_world["member"]
    resp = _auth(org_world["corp"]).patch(
        f"/api/accounts/users/{member.id}/", {"role": roles["group_admin"].id}, format="json"
    )
    assert resp.status_code == 400
    member.refresh_from_db()
    assert member.role.name == "individual"


def test_add_group_admin_flow_still_works(org_world):
    resp = _auth(org_world["corp"]).post(
        f"/api/organizations/{org_world['org'].id}/group-admins/",
        {"full_name": "G", "email": "g@t.com", "group_id": org_world["north"].id},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert User.objects.get(email="g@t.com").role.name == "group_admin"


# --- #7 ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra", [{"organization_id": "abc"}, {"group_id": "abc"}, {"group_id": "1.5"}]
)
def test_non_numeric_ids_are_refused_not_500(org_world, roles, extra):
    resp = _auth(org_world["corp"]).post(
        "/api/accounts/users/",
        {"email": "y@t.com", "full_name": "Y", "role": roles["individual"].id, **extra},
    )
    assert resp.status_code in (400, 403)
    assert "error" in resp.data
    assert not User.objects.filter(email="y@t.com").exists()


# --- #8 ----------------------------------------------------------------------


def _list_queries(client, url):
    with CaptureQueriesContext(connection) as ctx:
        resp = client.get(url)
    assert resp.status_code == 200
    return len(ctx.captured_queries)


def test_user_list_query_count_does_not_grow_per_row(org_world, roles):
    org, corp = org_world["org"], org_world["corp"]
    c = _auth(corp)
    for i in range(3):
        u = _user(roles, "individual", f"a{i}@t.com")
        OrganizationMember.objects.create(organization=org, user=u)
    few = _list_queries(c, "/api/accounts/users/?page_size=50")
    for i in range(15):
        u = _user(roles, "individual", f"b{i}@t.com")
        OrganizationMember.objects.create(organization=org, user=u)
    many = _list_queries(c, "/api/accounts/users/?page_size=50")
    assert many == few


def test_me_still_reports_org_disabled_modules(org_world):
    org = org_world["org"]
    org.enabled_modules = ["assessment"]
    org.save()
    data = _auth(org_world["corp"]).get("/api/me/").data["data"]
    assert "training" in data["disabled_modules"]
    assert all(r["module"] != "training" for r in data["module_rights"])
    # In the user list the manager's own row keeps the same view.
    rows = _auth(org_world["corp"]).get("/api/accounts/users/").data["data"]["results"]
    own = next(r for r in rows if r["email"] == "corp@t.com")
    assert own["disabled_modules"] == data["disabled_modules"]


# --- #11 ---------------------------------------------------------------------


def test_sync_migration_creates_missing_system_roles():
    migration = importlib.import_module("apps.accounts.migrations.0017_sync_system_role_rights")
    ModuleRight.objects.all().delete()
    Role.objects.all().delete()

    migration.sync(django_apps, None)

    names = set(Role.objects.values_list("name", flat=True))
    assert names == {code for code, _ in Role.ROLE_CHOICES}
    assert not Role.objects.filter(is_system=False).exists()
    assert not Role.objects.filter(is_frozen=False).exists()
    for name, perms in ROLE_PERMISSIONS.items():
        rights = set(ModuleRight.objects.filter(role__name=name).values_list("module", "action"))
        assert rights == set(perms), name
    # Idempotent.
    migration.sync(django_apps, None)
    assert Role.objects.count() == len(Role.ROLE_CHOICES)


def test_manager_bulk_upload_cannot_create_group_admins():
    """Group Admins come from the Add Group Admin form (tied to a group),
    never from a CSV where they would have no group."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    from rest_framework.test import APIClient

    from apps.accounts.models import ModuleRight, Role, User
    from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
    from apps.accounts.services import get_or_create_default_roles
    from apps.organizations.models import Organization, OrganizationMember

    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    org = Organization.objects.create(name="Bulk Org", type="corporate")
    mgr = User.objects.create_user(
        email="bulkmgr@t.com", password="pw", is_active=True, role=roles["corp_admin"]
    )
    OrganizationMember.objects.create(organization=org, user=mgr, is_admin=True)
    c = APIClient()
    c.force_authenticate(user=mgr)
    csv = (
        b"full_name,email,role_name\nGA One,ga1@t.com,group_admin\nInd One,ind1@t.com,individual\n"
    )
    resp = c.post(
        "/api/accounts/users/bulk-upload/",
        {"file": SimpleUploadedFile("u.csv", csv, content_type="text/csv")},
        format="multipart",
    )
    assert resp.status_code == 200, resp.data
    assert not User.objects.filter(email="ga1@t.com").exists()
    assert User.objects.filter(email="ind1@t.com").exists()
