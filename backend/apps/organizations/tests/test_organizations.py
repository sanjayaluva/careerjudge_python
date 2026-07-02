"""Tests for the organizations module."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory

User = get_user_model()


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def cj_admin_role(roles):
    return roles["cj_admin"]


@pytest.fixture
def corp_admin_role(roles):
    return roles["corp_admin"]


@pytest.fixture
def individual_role(roles):
    return roles["individual"]


@pytest.fixture
def cj_admin_user(db, cj_admin_role):
    """A CJ Admin user with organizations permissions."""
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=cj_admin_role, module="organizations", action=action)
    return UserFactory(role=cj_admin_role, email="admin@test.com")


@pytest.fixture
def corp_admin_user(db, corp_admin_role):
    """A Corporate Admin user with organizations view+change permissions."""
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(
            role=corp_admin_role, module="organizations", action=action
        )
    return UserFactory(role=corp_admin_role, email="corpadmin@test.com")


@pytest.fixture
def individual_user(db, individual_role):
    return UserFactory(role=individual_role, email="individual@test.com")


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def authed_client(client, cj_admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(cj_admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def corp_client(client, corp_admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(corp_admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def individual_client(client, individual_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(individual_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOrganizationList:
    def test_admin_can_list(self, authed_client):
        resp = authed_client.get("/api/organizations/")
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_individual_cannot_list(self, individual_client):
        resp = individual_client.get("/api/organizations/")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list(self, client):
        resp = client.get("/api/organizations/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestOrganizationCreate:
    def test_admin_can_create(self, authed_client):
        resp = authed_client.post(
            "/api/organizations/",
            {
                "name": "Acme Corp",
                "type": "corporate",
                "contact_email": "hr@acme.com",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Acme Corp"

    def test_duplicate_name(self, authed_client):
        authed_client.post(
            "/api/organizations/",
            {"name": "Acme Corp", "type": "corporate"},
            format="json",
        )
        resp = authed_client.post(
            "/api/organizations/",
            {"name": "Acme Corp", "type": "corporate"},
            format="json",
        )
        assert resp.status_code == 400

    def test_corp_admin_can_create(self, corp_client):
        resp = corp_client.post(
            "/api/organizations/",
            {"name": "Beta Corp", "type": "corporate"},
            format="json",
        )
        assert resp.status_code == 201

    def test_individual_cannot_create(self, individual_client):
        resp = individual_client.post(
            "/api/organizations/",
            {"name": "Gamma Corp", "type": "corporate"},
            format="json",
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestOrganizationRetrieve:
    def test_admin_can_retrieve(self, authed_client):
        create_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Delta Corp", "type": "corporate"},
            format="json",
        )
        org_id = create_resp.json()["data"]["id"]
        resp = authed_client.get(f"/api/organizations/{org_id}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Delta Corp"


@pytest.mark.django_db
class TestOrganizationUpdate:
    def test_admin_can_update(self, authed_client):
        create_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Epsilon Corp", "type": "corporate"},
            format="json",
        )
        org_id = create_resp.json()["data"]["id"]
        resp = authed_client.patch(
            f"/api/organizations/{org_id}/",
            {"description": "Updated description"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["description"] == "Updated description"


@pytest.mark.django_db
class TestOrganizationDelete:
    def test_admin_can_delete(self, authed_client):
        create_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Zeta Corp", "type": "corporate"},
            format="json",
        )
        org_id = create_resp.json()["data"]["id"]
        resp = authed_client.delete(f"/api/organizations/{org_id}/")
        assert resp.status_code == 200

    def test_corp_admin_cannot_delete(self, corp_client):
        create_resp = corp_client.post(
            "/api/organizations/",
            {"name": "Eta Corp", "type": "corporate"},
            format="json",
        )
        org_id = create_resp.json()["data"]["id"]
        resp = corp_client.delete(f"/api/organizations/{org_id}/")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Group CRUD
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGroupCRUD:
    def test_create_group(self, authed_client):
        org_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Theta Corp", "type": "corporate"},
            format="json",
        )
        org_id = org_resp.json()["data"]["id"]

        resp = authed_client.post(
            f"/api/organizations/{org_id}/groups",
            {"name": "Engineering", "description": "Engineering team"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Engineering"

    def test_list_groups(self, authed_client):
        org_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Iota Corp", "type": "corporate"},
            format="json",
        )
        org_id = org_resp.json()["data"]["id"]
        authed_client.post(
            f"/api/organizations/{org_id}/groups",
            {"name": "Sales"},
            format="json",
        )
        resp = authed_client.get(f"/api/organizations/{org_id}/groups")
        assert resp.status_code == 200

    def test_delete_group(self, authed_client):
        org_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Kappa Corp", "type": "corporate"},
            format="json",
        )
        org_id = org_resp.json()["data"]["id"]
        group_resp = authed_client.post(
            f"/api/organizations/{org_id}/groups",
            {"name": "Marketing"},
            format="json",
        )
        group_id = group_resp.json()["data"]["id"]
        resp = authed_client.delete(f"/api/organizations/{org_id}/groups/{group_id}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOrganizationMembers:
    def test_add_member(self, authed_client, individual_user):
        org_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Lambda Corp", "type": "corporate"},
            format="json",
        )
        org_id = org_resp.json()["data"]["id"]

        resp = authed_client.post(
            f"/api/organizations/{org_id}/members",
            {"user_email": individual_user.email},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["user"]["email"] == individual_user.email

    def test_add_member_nonexistent_user(self, authed_client):
        org_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Mu Corp", "type": "corporate"},
            format="json",
        )
        org_id = org_resp.json()["data"]["id"]

        resp = authed_client.post(
            f"/api/organizations/{org_id}/members",
            {"user_email": "nonexistent@test.com"},
            format="json",
        )
        assert resp.status_code == 400

    def test_add_duplicate_member(self, authed_client, individual_user):
        org_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Nu Corp", "type": "corporate"},
            format="json",
        )
        org_id = org_resp.json()["data"]["id"]

        authed_client.post(
            f"/api/organizations/{org_id}/members",
            {"user_email": individual_user.email},
            format="json",
        )
        resp = authed_client.post(
            f"/api/organizations/{org_id}/members",
            {"user_email": individual_user.email},
            format="json",
        )
        assert resp.status_code == 400

    def test_list_members(self, authed_client, individual_user):
        org_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Xi Corp", "type": "corporate"},
            format="json",
        )
        org_id = org_resp.json()["data"]["id"]
        authed_client.post(
            f"/api/organizations/{org_id}/members",
            {"user_email": individual_user.email},
            format="json",
        )
        resp = authed_client.get(f"/api/organizations/{org_id}/members")
        assert resp.status_code == 200

    def test_remove_member(self, authed_client, individual_user):
        org_resp = authed_client.post(
            "/api/organizations/",
            {"name": "Omicron Corp", "type": "corporate"},
            format="json",
        )
        org_id = org_resp.json()["data"]["id"]
        member_resp = authed_client.post(
            f"/api/organizations/{org_id}/members",
            {"user_email": individual_user.email},
            format="json",
        )
        member_id = member_resp.json()["data"]["id"]
        resp = authed_client.delete(f"/api/organizations/{org_id}/members/{member_id}")
        assert resp.status_code == 200
