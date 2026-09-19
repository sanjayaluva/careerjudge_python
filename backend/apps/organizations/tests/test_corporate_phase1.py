"""Corporate-Exclusive Phase 1: org-scoping + corporate user management.

Covers WP-A (org-scoping foundation + content visibility), WP-B (corporate user
management), and WP-C (Region/Division) from
docs/compliance/corporate_exclusive_scope.md.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, User
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment
from apps.organizations.models import (
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


def _grant(role, module, *actions):
    for a in actions:
        ModuleRight.objects.get_or_create(role=role, module=module, action=a)


def _auth(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


@pytest.fixture
def cj_admin(roles):
    r = roles["cj_admin"]
    _grant(r, "organizations", "view", "add", "change", "delete")
    _grant(r, "accounts", "view", "add", "change", "delete")
    _grant(r, "assessment", "view")
    return User.objects.create_user(email="cjadmin@t.com", password="pw", is_active=True, role=r)


@pytest.fixture
def corp_admin(roles):
    r = roles["corp_admin"]
    _grant(r, "organizations", "view", "add", "change")
    _grant(r, "accounts", "view", "add")
    return User.objects.create_user(email="corp@t.com", password="pw", is_active=True, role=r)


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme Corp", type="corporate")


@pytest.fixture
def corp_admin_in_org(corp_admin, org):
    OrganizationMember.objects.create(organization=org, user=corp_admin, is_admin=True)
    return corp_admin


# --------------------------------------------------------------------------
# WP-C — Region/Division + onboarding fields
# --------------------------------------------------------------------------


def test_group_carries_region_division(cj_admin, org):
    c = _auth(cj_admin)
    resp = c.post(
        f"/api/organizations/{org.id}/groups/",
        {"name": "Sales", "region_division": "North Zone"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["region_division"] == "North Zone"


def test_org_onboarding_manager_and_tax_id(cj_admin):
    c = _auth(cj_admin)
    resp = c.post(
        "/api/organizations/",
        {"name": "Globex", "type": "corporate", "manager_name": "Jane Roe", "tax_id": "AAAPL1234C"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["manager_name"] == "Jane Roe"
    assert resp.data["data"]["tax_id"] == "AAAPL1234C"


# --------------------------------------------------------------------------
# WP-B — corporate member onboarding
# --------------------------------------------------------------------------


def test_member_add_with_employee_id(cj_admin, org, roles):
    existing = User.objects.create_user(
        email="emp@t.com", password="pw", is_active=True, role=roles["individual"]
    )
    c = _auth(cj_admin)
    resp = c.post(
        f"/api/organizations/{org.id}/members/",
        {"user_email": "emp@t.com", "employee_id": "EMP7"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    m = OrganizationMember.objects.get(organization=org, user=existing)
    assert m.employee_id == "EMP7"


def test_member_add_creates_new_user_when_full_name_given(cj_admin, org):
    c = _auth(cj_admin)
    resp = c.post(
        f"/api/organizations/{org.id}/members/",
        {"user_email": "newhire@t.com", "full_name": "New Hire", "employee_id": "EMP9"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    user = User.objects.get(email="newhire@t.com")
    assert user.full_name == "New Hire"
    assert user.is_active is False  # must verify email
    assert OrganizationMember.objects.filter(organization=org, user=user).exists()


def test_member_add_missing_user_without_full_name_still_errors(cj_admin, org):
    c = _auth(cj_admin)
    resp = c.post(
        f"/api/organizations/{org.id}/members/",
        {"user_email": "ghost@t.com"},
        format="json",
    )
    assert resp.status_code == 400


def test_corp_admin_created_user_is_linked_to_their_org(corp_admin_in_org, org):
    c = _auth(corp_admin_in_org)
    resp = c.post(
        "/api/accounts/users/",
        {"email": "employee@t.com", "full_name": "Emp One", "employee_id": "E100"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    user = User.objects.get(email="employee@t.com")
    m = OrganizationMember.objects.get(organization=org, user=user)
    assert m.employee_id == "E100"


# --------------------------------------------------------------------------
# WP-B — CJ_UC003 / CJ_UC004: CJ Admin cannot modify/delete corporate users
# --------------------------------------------------------------------------


def _corporate_individual(org, roles, email="worker@t.com"):
    u = User.objects.create_user(
        email=email, password="pw", is_active=True, role=roles["individual"]
    )
    OrganizationMember.objects.create(organization=org, user=u, is_admin=False)
    return u


def test_cj_admin_cannot_delete_corporate_individual(cj_admin, org, roles):
    worker = _corporate_individual(org, roles)
    c = _auth(cj_admin)
    resp = c.delete(f"/api/accounts/users/{worker.id}/")
    assert resp.status_code == 403
    assert User.objects.filter(id=worker.id).exists()


def test_cj_admin_cannot_modify_corporate_individual(cj_admin, org, roles):
    worker = _corporate_individual(org, roles)
    c = _auth(cj_admin)
    resp = c.patch(f"/api/accounts/users/{worker.id}/", {"full_name": "Renamed"}, format="json")
    assert resp.status_code == 403


def test_cj_admin_can_still_delete_non_corporate_individual(cj_admin, roles):
    plain = User.objects.create_user(
        email="plain@t.com", password="pw", is_active=True, role=roles["individual"]
    )
    c = _auth(cj_admin)
    resp = c.delete(f"/api/accounts/users/{plain.id}/")
    assert resp.status_code == 200
    assert not User.objects.filter(id=plain.id).exists()


# --------------------------------------------------------------------------
# WP-A — assignment API + corporate content visibility (CJ_UC030)
# --------------------------------------------------------------------------


def test_assignment_crud(cj_admin, org):
    a = Assessment.objects.create(title="Aptitude", status="published")
    c = _auth(cj_admin)
    resp = c.post(
        f"/api/organizations/{org.id}/assignments/",
        {"item_type": "assessment", "item_id": a.id},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    # Duplicate rejected
    dup = c.post(
        f"/api/organizations/{org.id}/assignments/",
        {"item_type": "assessment", "item_id": a.id},
        format="json",
    )
    assert dup.status_code == 400
    lst = c.get(f"/api/organizations/{org.id}/assignments/")
    assert len(lst.data["data"]["results"]) == 1


def test_corporate_individual_sees_only_assigned_assessments(cj_admin, org, roles):
    assigned = Assessment.objects.create(title="Assigned", status="published")
    Assessment.objects.create(title="Unassigned", status="published")
    OrganizationAssignment.objects.create(
        organization=org, item_type="assessment", item_id=assigned.id
    )
    worker = _corporate_individual(org, roles)
    _grant(roles["individual"], "assessment", "view")

    resp = _auth(worker).get("/api/assessments/")
    assert resp.status_code == 200, resp.data
    titles = {row["title"] for row in resp.data["data"]["results"]}
    assert titles == {"Assigned"}


def test_non_corporate_individual_sees_all_published(cj_admin, roles):
    Assessment.objects.create(title="Pub1", status="published")
    Assessment.objects.create(title="Pub2", status="published")
    plain = User.objects.create_user(
        email="free@t.com", password="pw", is_active=True, role=roles["individual"]
    )
    _grant(roles["individual"], "assessment", "view")

    resp = _auth(plain).get("/api/assessments/")
    assert resp.status_code == 200, resp.data
    titles = {row["title"] for row in resp.data["data"]["results"]}
    assert {"Pub1", "Pub2"}.issubset(titles)
