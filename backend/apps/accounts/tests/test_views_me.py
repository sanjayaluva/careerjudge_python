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
