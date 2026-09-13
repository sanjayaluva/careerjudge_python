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

    def test_invited_user_gets_verification_token_and_can_activate(
        self, authed_client, individual_role, mailoutbox
    ):
        """D9 §2.2-2.3: an admin-created (invited) user must be able to activate."""
        from rest_framework.test import APIClient

        from apps.accounts.models import EmailVerificationToken

        resp = authed_client.post(
            "/api/accounts/users/",
            {
                "email": "invited@test.com",
                "full_name": "Invited User",
                "is_active": False,
                "is_email_verified": False,
                "role": individual_role.id,
            },
            format="json",
        )
        assert resp.status_code == 201
        user = User.objects.get(email="invited@test.com")
        assert user.is_active is False

        token = EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).first()
        assert token is not None
        assert len(mailoutbox) == 1

        anon = APIClient()
        verify_resp = anon.post(
            "/api/auth/verify-email", {"token": str(token.token)}, format="json"
        )
        assert verify_resp.status_code == 200
        user.refresh_from_db()
        assert user.is_active is True
        assert user.is_email_verified is True

        # The admin generated a random password the invitee never saw; once
        # they know a password (e.g. via reset), login must work now that
        # the account is active.
        user.set_password("KnownPass123!")
        user.save(update_fields=["password"])
        login_resp = anon.post(
            "/api/auth/login",
            {"email": user.email, "password": "KnownPass123!"},
            format="json",
        )
        assert login_resp.status_code == 200


@pytest.mark.django_db
class TestUserCreateRoleSpecificProfileFields:
    """D9: the admin Add-User form captures role-specific fields (org name,
    PAN/TAN, agency, allocated region, ...) for the role being created."""

    def test_create_channel_partner_with_agency_fields(self, authed_client, db):
        role, _ = Role.objects.get_or_create(
            name="channel_partner", defaults={"is_system": True, "is_frozen": True}
        )
        resp = authed_client.post(
            "/api/accounts/users/",
            {
                "email": "partner@test.com",
                "full_name": "Partner Person",
                "is_active": True,
                "is_email_verified": True,
                "role": role.id,
                "profile": {
                    "agency_name": "Acme Partners",
                    "allocated_region": "APAC",
                },
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        user = User.objects.get(email="partner@test.com")
        assert user.profile.agency_name == "Acme Partners"
        assert user.profile.allocated_region == "APAC"

    def test_create_corp_admin_with_manager_and_tan(self, authed_client, db):
        role, _ = Role.objects.get_or_create(
            name="corp_admin", defaults={"is_system": True, "is_frozen": True}
        )
        resp = authed_client.post(
            "/api/accounts/users/",
            {
                "email": "corp@test.com",
                "full_name": "Corp Person",
                "is_active": True,
                "is_email_verified": True,
                "role": role.id,
                "profile": {
                    "manager_name": "Jane Manager",
                    "tan_number": "TAN12345",
                    "pan_number": "PAN67890",
                },
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        user = User.objects.get(email="corp@test.com")
        assert user.profile.manager_name == "Jane Manager"
        assert user.profile.tan_number == "TAN12345"
        assert user.profile.pan_number == "PAN67890"

    def test_update_user_profile_fields(self, authed_client, individual_user):
        resp = authed_client.patch(
            f"/api/accounts/users/{individual_user.id}/",
            {"profile": {"occupation": "employed", "current_position": "Engineer"}},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        individual_user.refresh_from_db()
        assert individual_user.profile.occupation == "employed"
        assert individual_user.profile.current_position == "Engineer"

    def test_unknown_profile_keys_are_ignored(self, authed_client, individual_role):
        """Unrecognized keys in `profile` must not raise — same tolerant
        behavior as the self-service /api/me/ profile update."""
        resp = authed_client.post(
            "/api/accounts/users/",
            {
                "email": "tolerant@test.com",
                "full_name": "Tolerant",
                "is_active": True,
                "is_email_verified": True,
                "role": individual_role.id,
                "profile": {"not_a_real_field": "whatever", "occupation": "employed"},
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        user = User.objects.get(email="tolerant@test.com")
        assert user.profile.occupation == "employed"


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
        assert resp.json()["data"]["count"] == 12  # 12 default roles (incl. helpdesk)


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
