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
