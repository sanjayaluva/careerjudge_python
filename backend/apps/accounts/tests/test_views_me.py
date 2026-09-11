"""Tests for /api/me/ endpoints."""

import pytest


@pytest.mark.django_db
class TestMeView:
    def test_get_me(self, authed_client, cj_admin_user):
        resp = authed_client.get("/api/me/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == cj_admin_user.email
        assert data["id"] == cj_admin_user.id
        assert "profile" in data

    def test_get_me_includes_module_rights(self, authed_client, cj_admin_user):
        """/api/me/ must expose the user's effective ModuleRights — the RBAC
        single source of truth the frontend derives nav + action gating from."""
        resp = authed_client.get("/api/me/")
        assert resp.status_code == 200
        rights = resp.json()["data"]["module_rights"]
        assert {"module": "accounts", "action": "view"} in rights
        assert {"module": "accounts", "action": "delete"} in rights

    def test_get_me_module_rights_empty_when_no_role(self, client):
        """A user with no role gets an empty module_rights list, not a crash."""
        from rest_framework_simplejwt.tokens import RefreshToken

        from .factories import UserFactory

        user = UserFactory(role=None, email="no-role@test.com")
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = client.get("/api/me/")
        assert resp.status_code == 200
        assert resp.json()["data"]["module_rights"] == []

    def test_get_me_module_rights_for_custom_role(self, client, individual_role):
        """A custom role's own grants AND its base_role's inherited grants both
        surface in module_rights — proving effective_rights (incl. base_role
        inheritance) is what feeds the response, not just the role's own rows."""
        from rest_framework_simplejwt.tokens import RefreshToken

        from apps.accounts.models import ModuleRight, Role

        from .factories import UserFactory

        # base_role (individual) gets a grant that should be *inherited*.
        ModuleRight.objects.create(role=individual_role, module="training", action="view")

        custom_role = Role.objects.create(name="Custom QA Role", base_role=individual_role)
        # the custom role gets its own additional grant.
        ModuleRight.objects.create(role=custom_role, module="cms", action="approve")

        user = UserFactory(role=custom_role, email="customrole@test.com")
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        resp = client.get("/api/me/")
        assert resp.status_code == 200
        rights = resp.json()["data"]["module_rights"]
        assert {"module": "cms", "action": "approve"} in rights  # own grant
        assert {"module": "training", "action": "view"} in rights  # inherited

    def test_get_me_unauthenticated(self, client):
        resp = client.get("/api/me/")
        assert resp.status_code == 401

    def test_patch_me_basic_fields(self, authed_client, cj_admin_user):
        resp = authed_client.patch(
            "/api/me/",
            {
                "full_name": "Updated Name",
                "phone": "+9999999999",
            },
            format="json",
        )
        assert resp.status_code == 200
        cj_admin_user.refresh_from_db()
        assert cj_admin_user.full_name == "Updated Name"
        assert cj_admin_user.phone == "+9999999999"

    def test_patch_me_with_profile(self, authed_client, cj_admin_user):
        resp = authed_client.patch(
            "/api/me/",
            {
                "profile": {
                    "gender": "female",
                    "mobile": "+8888888888",
                    "city": "Mumbai",
                },
            },
            format="json",
        )
        assert resp.status_code == 200
        cj_admin_user.refresh_from_db()
        assert cj_admin_user.profile.gender == "female"
        assert cj_admin_user.profile.city == "Mumbai"

    def test_patch_me_gender_other(self, authed_client, cj_admin_user):
        """Gender 'other' should be accepted (matches frontend schema)."""
        resp = authed_client.patch(
            "/api/me/",
            {"profile": {"gender": "other"}},
            format="json",
        )
        assert resp.status_code == 200
        cj_admin_user.refresh_from_db()
        assert cj_admin_user.profile.gender == "other"

    def test_patch_me_with_all_profile_fields(self, authed_client, cj_admin_user):
        """All profile fields should be updateable."""
        resp = authed_client.patch(
            "/api/me/",
            {
                "profile": {
                    "gender": "male",
                    "mobile": "+1234567890",
                    "date_of_birth": "1990-01-15",
                    "address_line1": "123 Main St",
                    "address_line2": "Apt 4B",
                    "city": "New York",
                    "state": "NY",
                    "country": "USA",
                    "postal_code": "10001",
                    "bio": "Software engineer",
                }
            },
            format="json",
        )
        assert resp.status_code == 200
        cj_admin_user.refresh_from_db()
        assert cj_admin_user.profile.gender == "male"
        assert cj_admin_user.profile.mobile == "+1234567890"
        assert cj_admin_user.profile.city == "New York"
        assert cj_admin_user.profile.bio == "Software engineer"


@pytest.mark.django_db
class TestChangePassword:
    def test_happy_path(self, authed_client, cj_admin_user):
        old_pw = cj_admin_user._raw_password
        resp = authed_client.post(
            "/api/me/change-password",
            {
                "old_password": old_pw,
                "new_password": "BrandNewP@ss3",
            },
            format="json",
        )
        assert resp.status_code == 200
        cj_admin_user.refresh_from_db()
        assert cj_admin_user.check_password("BrandNewP@ss3")

    def test_wrong_old_password(self, authed_client):
        resp = authed_client.post(
            "/api/me/change-password",
            {
                "old_password": "WrongOldP@ss",
                "new_password": "BrandNewP@ss3",
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "old_password" in resp.json()["error"]["details"]

    def test_weak_new_password(self, authed_client, cj_admin_user):
        resp = authed_client.post(
            "/api/me/change-password",
            {
                "old_password": cj_admin_user._raw_password,
                "new_password": "weak",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_unauthenticated(self, client):
        resp = client.post(
            "/api/me/change-password",
            {
                "old_password": "x",
                "new_password": "y",
            },
            format="json",
        )
        assert resp.status_code == 401
