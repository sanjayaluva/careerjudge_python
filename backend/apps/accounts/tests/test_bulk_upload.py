"""Tests for bulk user upload + CSV template download."""

import csv
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User


@pytest.mark.django_db
class TestBulkUserUpload:
    def test_happy_path(self, authed_client, individual_role):
        """Upload a CSV with 2 valid users → both created."""
        csv_content = "full_name,email,phone,role_name\nJohn Doe,john1@bulk.com,+1234567890,individual\nJane Smith,jane1@bulk.com,,\n"
        file = SimpleUploadedFile("users.csv", csv_content.encode("utf-8"), content_type="text/csv")

        resp = authed_client.post(
            "/api/accounts/users/bulk-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["created_count"] == 2
        assert data["skipped_count"] == 0
        assert data["error_count"] == 0
        assert User.objects.filter(email="john1@bulk.com").exists()
        assert User.objects.filter(email="jane1@bulk.com").exists()

    def test_duplicate_email_skipped(self, authed_client, individual_user):
        """CSV with an existing email → skipped."""
        csv_content = (
            f"full_name,email\nDuplicate,{individual_user.email}\nNew User,new1@bulk.com\n"
        )
        file = SimpleUploadedFile("users.csv", csv_content.encode("utf-8"), content_type="text/csv")

        resp = authed_client.post(
            "/api/accounts/users/bulk-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["created_count"] == 1
        assert data["skipped_count"] == 1
        assert data["error_count"] == 0

    def test_missing_required_columns(self, authed_client):
        """CSV without 'email' column → 400 error."""
        csv_content = "full_name,phone\nJohn Doe,+1234567890\n"
        file = SimpleUploadedFile("users.csv", csv_content.encode("utf-8"), content_type="text/csv")

        resp = authed_client.post(
            "/api/accounts/users/bulk-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 400
        assert "Missing required" in resp.json()["error"]["message"]

    def test_no_file_uploaded(self, authed_client):
        """No file in request → 400 error."""
        resp = authed_client.post("/api/accounts/users/bulk-upload/", {}, format="multipart")
        assert resp.status_code == 400
        assert "No file" in resp.json()["error"]["message"]

    def test_non_csv_file_rejected(self, authed_client):
        """Non-CSV file → 400 error."""
        file = SimpleUploadedFile("users.txt", b"hello", content_type="text/plain")
        resp = authed_client.post(
            "/api/accounts/users/bulk-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 400
        assert "CSV" in resp.json()["error"]["message"]

    def test_empty_name_error(self, authed_client):
        """CSV row with empty name → error."""
        csv_content = "full_name,email\n,badname@bulk.com\n"
        file = SimpleUploadedFile("users.csv", csv_content.encode("utf-8"), content_type="text/csv")

        resp = authed_client.post(
            "/api/accounts/users/bulk-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["error_count"] == 1
        assert data["created_count"] == 0

    def test_invalid_role_name_error(self, authed_client):
        """CSV with invalid role_name → error."""
        csv_content = "full_name,email,role_name\nTest User,test1@bulk.com,nonexistent_role\n"
        file = SimpleUploadedFile("users.csv", csv_content.encode("utf-8"), content_type="text/csv")

        resp = authed_client.post(
            "/api/accounts/users/bulk-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["error_count"] == 1
        assert "not found" in data["errors"][0]["error"]

    def test_individual_cannot_upload(self, individual_client):
        """Individual user (no accounts.add permission) → 403."""
        csv_content = "full_name,email\nTest,test2@bulk.com\n"
        file = SimpleUploadedFile("users.csv", csv_content.encode("utf-8"), content_type="text/csv")

        resp = individual_client.post(
            "/api/accounts/users/bulk-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 403

    def test_bulk_created_user_gets_verification_token_and_can_activate(
        self, authed_client, mailoutbox
    ):
        """D9 §2.2-2.3: bulk-invited users must be able to activate + log in."""
        from rest_framework.test import APIClient

        from apps.accounts.models import EmailVerificationToken

        csv_content = "full_name,email\nBulk Invitee,bulkinvite@bulk.com\n"
        file = SimpleUploadedFile("users.csv", csv_content.encode("utf-8"), content_type="text/csv")

        resp = authed_client.post(
            "/api/accounts/users/bulk-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["created_count"] == 1

        user = User.objects.get(email="bulkinvite@bulk.com")
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

        user.set_password("KnownPass123!")
        user.save(update_fields=["password"])
        login_resp = anon.post(
            "/api/auth/login",
            {"email": user.email, "password": "KnownPass123!"},
            format="json",
        )
        assert login_resp.status_code == 200


@pytest.mark.django_db
class TestBulkUserTemplate:
    def test_download_template(self, authed_client):
        """GET template → returns CSV with correct headers."""
        resp = authed_client.get("/api/accounts/users/bulk-upload/template/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        assert "attachment" in resp["Content-Disposition"]

        # Parse the CSV
        reader = csv.reader(io.StringIO(resp.content.decode("utf-8")))
        rows = list(reader)
        assert rows[0] == ["full_name", "email", "phone", "role_name"]
        assert "John Doe" in rows[1]
