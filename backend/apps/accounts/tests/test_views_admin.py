"""Tests for /api/accounts/ admin endpoints (users + roles CRUD)."""

import pytest

from apps.accounts.models import ModuleRight, Role, User


@pytest.mark.django_db
class TestUserList:
    def test_admin_can_list(self, authed_client):
        resp = authed_client.get("/api/accounts/users/")
        assert resp.status_code == 200
        body = resp.json()
        # list response is wrapped: { message, data: { count, results, ... } }
        assert "data" in body
        assert "results" in body["data"]
        assert body["data"]["count"] >= 1

    def test_individual_cannot_list(self, individual_client):
        resp = individual_client.get("/api/accounts/users/")
        # individual role has no 'view' right on accounts module
        assert resp.status_code == 403

    def test_unauthenticated(self, client):
        resp = client.get("/api/accounts/users/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestUserCreate:
    def test_admin_can_create(self, authed_client, individual_role):
        resp = authed_client.post(
            "/api/accounts/users/",
            {
                "email": "newuser2@test.com",
                "full_name": "New User 2",
                "is_active": True,
                "is_email_verified": True,
                "role": individual_role.id,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert User.objects.filter(email="newuser2@test.com").exists()

    def test_duplicate_email(self, authed_client, individual_user):
        resp = authed_client.post(
            "/api/accounts/users/",
            {
                "email": individual_user.email,
                "full_name": "Dup",
                "is_active": True,
                "is_email_verified": True,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_individual_cannot_create(self, individual_client):
        resp = individual_client.post(
            "/api/accounts/users/",
            {
                "email": "x@y.com",
                "full_name": "x",
                "is_active": True,
                "is_email_verified": True,
            },
            format="json",
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestUserRetrieve:
    def test_admin_can_retrieve(self, authed_client, cj_admin_user):
        resp = authed_client.get(f"/api/accounts/users/{cj_admin_user.id}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == cj_admin_user.email

    def test_retrieve_nonexistent(self, authed_client):
        resp = authed_client.get("/api/accounts/users/99999/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestUserUpdate:
    def test_admin_can_update(self, authed_client, individual_user):
        resp = authed_client.patch(
            f"/api/accounts/users/{individual_user.id}/",
            {
                "full_name": "Updated Individual",
            },
            format="json",
        )
        assert resp.status_code == 200
        individual_user.refresh_from_db()
        assert individual_user.full_name == "Updated Individual"


@pytest.mark.django_db
class TestUserDelete:
    def test_admin_can_delete_non_individual(self, authed_client, cj_admin_role, db):
        from .factories import UserFactory

        # trainer role, not individual — should be deletable
        trainer_role = Role.objects.get(name="trainer")
        user = UserFactory(role=trainer_role)
        resp = authed_client.delete(f"/api/accounts/users/{user.id}/")
        assert resp.status_code == 200
        assert not User.objects.filter(id=user.id).exists()

    def test_cj_admin_can_delete_individual(self, authed_client, individual_user):
        """CJ Admin CAN delete individual users (for bulk upload cleanup)."""
        resp = authed_client.delete(f"/api/accounts/users/{individual_user.id}/")
        assert resp.status_code == 200
        assert not User.objects.filter(id=individual_user.id).exists()

    def test_individual_cannot_delete_individual(self, individual_client, individual_user, db):
        """Individual users cannot delete other individual users."""
        from .factories import UserFactory

        other = UserFactory(role=individual_user.role, email="other@test.com")
        resp = individual_client.delete(f"/api/accounts/users/{other.id}/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestAssignRole:
    def test_happy_path(self, authed_client, individual_user, cj_admin_role):
        resp = authed_client.post(
            f"/api/accounts/users/{individual_user.id}/assign-role/",
            {"role_name": "cj_admin"},
            format="json",
        )
        assert resp.status_code == 200
        individual_user.refresh_from_db()
        assert individual_user.role.name == "cj_admin"

    def test_invalid_role(self, authed_client, individual_user):
        resp = authed_client.post(
            f"/api/accounts/users/{individual_user.id}/assign-role/",
            {"role_name": "nonexistent_role"},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestRoleList:
    def test_admin_can_list_roles(self, authed_client):
        resp = authed_client.get("/api/accounts/roles/")
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 11  # 11 default roles


@pytest.mark.django_db
class TestRoleCreate:
    def test_admin_can_create_custom_role(self, authed_client, individual_role):
        """Admin can create a custom role with a new name + base_role."""
        resp = authed_client.post(
            "/api/accounts/roles/",
            {
                "name": "Senior Reviewer",
                "description": "Reviewer with extra permissions",
                "base_role": individual_role.id,
            },
            format="json",
        )
        assert resp.status_code == 201
        from apps.accounts.models import Role

        role = Role.objects.get(name="Senior Reviewer")
        assert role.is_system is False
        assert role.is_frozen is False
        assert role.base_role_id == individual_role.id

    def test_cannot_create_role_with_system_name(self, authed_client):
        """Cannot create a custom role with a system role name."""
        resp = authed_client.post(
            "/api/accounts/roles/",
            {"name": "individual", "description": "Duplicate"},
            format="json",
        )
        assert resp.status_code == 400

    def test_cannot_create_role_with_duplicate_name(self, authed_client):
        """Cannot create a custom role with an existing role name."""
        # First create a custom role
        authed_client.post(
            "/api/accounts/roles/",
            {"name": "Senior Reviewer", "description": "First"},
            format="json",
        )
        # Try to create another with the same name
        resp = authed_client.post(
            "/api/accounts/roles/",
            {"name": "Senior Reviewer", "description": "Duplicate"},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestRoleRetrieve:
    def test_admin_can_retrieve_role(self, authed_client, cj_admin_role):
        resp = authed_client.get(f"/api/accounts/roles/{cj_admin_role.id}/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "cj_admin"
        assert data["is_system"] is True
        assert "rights" in data
        assert "effective_rights" in data


@pytest.mark.django_db
class TestAssignPermission:
    def test_happy_path_custom_role(self, authed_client, individual_role):
        """Can add a permission to a CUSTOM role (not a system role)."""
        # Create a custom role based on individual
        resp = authed_client.post(
            "/api/accounts/roles/",
            {"name": "Power User", "base_role": individual_role.id},
            format="json",
        )
        assert resp.status_code == 201
        custom_role_id = resp.json()["data"]["id"]

        # Now assign a permission to the custom role
        resp = authed_client.post(
            f"/api/accounts/roles/{custom_role_id}/assign-permission/",
            {"module": "accounts", "action": "view"},
            format="json",
        )
        assert resp.status_code == 201
        from apps.accounts.models import Role

        role = Role.objects.get(id=custom_role_id)
        assert ModuleRight.objects.filter(role=role, module="accounts", action="view").exists()

    def test_cannot_assign_permission_to_system_role(self, authed_client, individual_role):
        """Cannot add a permission to a SYSTEM (frozen) role."""
        resp = authed_client.post(
            f"/api/accounts/roles/{individual_role.id}/assign-permission/",
            {"module": "accounts", "action": "view"},
            format="json",
        )
        assert resp.status_code == 403
        assert "system" in resp.json()["error"]["message"].lower()

    def test_idempotent(self, authed_client, individual_role):
        """Assigning same permission twice to a custom role should not error."""
        # Create a custom role
        resp = authed_client.post(
            "/api/accounts/roles/",
            {"name": "Power User 2", "base_role": individual_role.id},
            format="json",
        )
        custom_role_id = resp.json()["data"]["id"]

        for _ in range(2):
            resp = authed_client.post(
                f"/api/accounts/roles/{custom_role_id}/assign-permission/",
                {"module": "accounts", "action": "view"},
                format="json",
            )
            assert resp.status_code == 201
