"""Tests for auth endpoints: signup, login, logout, verify-email, reset-password."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User,
)


@pytest.mark.django_db
class TestSignup:
    def test_happy_path(self, client):
        resp = client.post(
            "/api/auth/signup",
            {
                "email": "newuser@example.com",
                "password": "StrongP@ss1",
                "full_name": "New User",
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["email"] == "newuser@example.com"
        # user should exist, inactive, unverified
        user = User.objects.get(email="newuser@example.com")
        assert user.is_active is False
        assert user.is_email_verified is False
        # default 'individual' role assigned if it exists
        if hasattr(user, "role") and user.role:
            assert user.role.name == "individual"
        # verification token created
        assert EmailVerificationToken.objects.filter(user=user).count() == 1

    def test_duplicate_email(self, client, individual_user):
        resp = client.post(
            "/api/auth/signup",
            {
                "email": individual_user.email,
                "password": "StrongP@ss1",
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "already exists" in str(resp.json()["error"]["details"]["email"])

    def test_weak_password(self, client):
        resp = client.post(
            "/api/auth/signup",
            {
                "email": "x@y.com",
                "password": "weak",
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "password" in resp.json()["error"]["details"]

    def test_missing_email(self, client):
        resp = client.post(
            "/api/auth/signup",
            {
                "password": "StrongP@ss1",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_email_case_insensitive(self, client, individual_user):
        resp = client.post(
            "/api/auth/signup",
            {
                "email": individual_user.email.upper(),
                "password": "StrongP@ss1",
            },
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_happy_path(self, client, individual_user):
        resp = client.post(
            "/api/auth/login",
            {
                "email": individual_user.email,
                "password": individual_user._raw_password,
            },
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == individual_user.email

    def test_invalid_password(self, client, individual_user):
        resp = client.post(
            "/api/auth/login",
            {
                "email": individual_user.email,
                "password": "WrongPassword123!",
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "Invalid credentials" in str(resp.json()["error"])

    def test_nonexistent_user(self, client):
        resp = client.post(
            "/api/auth/login",
            {
                "email": "ghost@nowhere.com",
                "password": "Whatever123!",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_inactive_account(self, client, db, individual_role):
        from .factories import UserFactory

        user = UserFactory(role=individual_role, is_active=False, is_email_verified=False)
        resp = client.post(
            "/api/auth/login",
            {
                "email": user.email,
                "password": user._raw_password,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "not activated" in str(resp.json()["error"]).lower()


@pytest.mark.django_db
class TestLogout:
    def test_happy_path(self, authed_client, cj_admin_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(cj_admin_user)
        resp = authed_client.post("/api/auth/logout", {"refresh": str(refresh)}, format="json")
        assert resp.status_code == 200

    def test_missing_refresh(self, authed_client):
        resp = authed_client.post("/api/auth/logout", {}, format="json")
        assert resp.status_code == 400

    def test_unauthenticated(self, client):
        resp = client.post("/api/auth/logout", {"refresh": "x"}, format="json")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestVerifyEmail:
    def test_happy_path(self, client, db, individual_role):
        from .factories import UserFactory

        user = UserFactory(role=individual_role, is_active=False, is_email_verified=False)
        token = EmailVerificationToken.objects.create(user=user)
        resp = client.post("/api/auth/verify-email", {"token": str(token.token)}, format="json")
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.is_email_verified is True
        assert user.is_active is True
        token.refresh_from_db()
        assert token.used_at is not None

    def test_invalid_token(self, client):
        import uuid

        resp = client.post("/api/auth/verify-email", {"token": str(uuid.uuid4())}, format="json")
        assert resp.status_code == 400

    def test_expired_token(self, client, db, individual_role):
        from .factories import UserFactory

        user = UserFactory(role=individual_role, is_active=False, is_email_verified=False)
        token = EmailVerificationToken.objects.create(user=user)
        token.expires_at = timezone.now() - timedelta(hours=1)
        token.save()
        resp = client.post("/api/auth/verify-email", {"token": str(token.token)}, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestResendVerification:
    def test_happy_path(self, client, db, individual_role):
        from .factories import UserFactory

        user = UserFactory(role=individual_role, is_active=False, is_email_verified=False)
        resp = client.post("/api/auth/resend-verification", {"email": user.email}, format="json")
        assert resp.status_code == 200
        # new token created
        assert EmailVerificationToken.objects.filter(user=user).count() >= 1

    def test_nonexistent_email_no_leak(self, client):
        resp = client.post(
            "/api/auth/resend-verification", {"email": "ghost@nowhere.com"}, format="json"
        )
        assert resp.status_code == 200  # silent success


@pytest.mark.django_db
class TestForgotPassword:
    def test_happy_path(self, client, individual_user):
        resp = client.post(
            "/api/auth/forgot-password", {"email": individual_user.email}, format="json"
        )
        assert resp.status_code == 200
        assert PasswordResetToken.objects.filter(user=individual_user).count() == 1

    def test_nonexistent_email_no_leak(self, client):
        resp = client.post(
            "/api/auth/forgot-password", {"email": "ghost@nowhere.com"}, format="json"
        )
        assert resp.status_code == 200  # silent success
        assert "If an account" in resp.json()["message"]


@pytest.mark.django_db
class TestResetPassword:
    def test_happy_path(self, client, individual_user):
        token = PasswordResetToken.objects.create(user=individual_user)
        new_pw = "BrandNewP@ss2"
        resp = client.post(
            "/api/auth/reset-password",
            {
                "token": str(token.token),
                "password": new_pw,
            },
            format="json",
        )
        assert resp.status_code == 200
        individual_user.refresh_from_db()
        assert individual_user.check_password(new_pw)
        token.refresh_from_db()
        assert token.used_at is not None

    def test_invalid_token(self, client):
        import uuid

        resp = client.post(
            "/api/auth/reset-password",
            {
                "token": str(uuid.uuid4()),
                "password": "BrandNewP@ss2",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_weak_password(self, client, individual_user):
        token = PasswordResetToken.objects.create(user=individual_user)
        resp = client.post(
            "/api/auth/reset-password",
            {
                "token": str(token.token),
                "password": "weak",
            },
            format="json",
        )
        assert resp.status_code == 400
