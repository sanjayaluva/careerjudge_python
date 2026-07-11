"""Tests for the seed_demo management command."""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.accounts.models import ModuleRight, Role, User


@pytest.mark.django_db
class TestSeedDemoCommand:
    def test_creates_all_roles(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        assert Role.objects.count() == 11
        for code, _ in Role.ROLE_CHOICES:
            assert Role.objects.filter(name=code).exists()

    def test_creates_demo_users(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        # 10 demo users + 1 superuser
        assert User.objects.count() == 12
        assert User.objects.filter(email="cj.admin@demo.careerjudge.pp.ua").exists()
        assert User.objects.filter(email="sme@demo.careerjudge.pp.ua").exists()
        assert User.objects.filter(email="reviewer@demo.careerjudge.pp.ua").exists()
        assert User.objects.filter(email="superuser@careerjudge.pp.ua", is_superuser=True).exists()

    def test_assigns_permissions_to_roles(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        # cj_admin should have many permissions
        cj_admin_role = Role.objects.get(name="cj_admin")
        assert ModuleRight.objects.filter(role=cj_admin_role).count() >= 10

    def test_idempotent(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        # Run again — should not duplicate
        call_command("seed_demo", stdout=out)
        assert Role.objects.count() == 11
        assert User.objects.count() == 12

    def test_demo_user_can_login(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        user = User.objects.get(email="cj.admin@demo.careerjudge.pp.ua")
        assert user.check_password("Demo@1234") is True
        assert user.is_active is True
        assert user.is_email_verified is True

    def test_seed_resets_password_for_existing_user(self):
        """Re-running seed_demo must reset passwords to the documented value.

        Without this, demo users created earlier with a different password
        cause 'Invalid credentials' errors — the documented credentials
        in README.md stop working.
        """
        out = StringIO()
        call_command("seed_demo", stdout=out)
        # Change the password to something wrong
        user = User.objects.get(email="individual@demo.careerjudge.pp.ua")
        user.set_password("WrongPassword123")
        user.save()
        assert user.check_password("Demo@1234") is False
        # Re-run seed_demo — should reset the password back
        call_command("seed_demo", stdout=out)
        user.refresh_from_db()
        assert user.check_password("Demo@1234") is True

    def test_seed_resets_superuser_password(self):
        """Re-running seed_demo must also reset the superuser password."""
        out = StringIO()
        call_command("seed_demo", stdout=out)
        superuser = User.objects.get(email="superuser@careerjudge.pp.ua")
        superuser.set_password("WrongSuperPassword")
        superuser.save()
        # Re-run
        call_command("seed_demo", stdout=out)
        superuser.refresh_from_db()
        assert superuser.check_password("Su@12345678") is True
