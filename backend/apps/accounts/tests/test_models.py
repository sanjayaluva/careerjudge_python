"""Tests for accounts models."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import (
    EmailVerificationToken,
    ModuleRight,
    PasswordResetToken,
    User,
)

from .factories import RoleFactory, UserFactory, UserProfileFactory


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="StrongP@ss1",
            full_name="Test User",
        )
        assert user.pk is not None
        assert user.is_active is False  # default per UC001
        assert user.is_email_verified is False
        assert user.check_password("StrongP@ss1")

    def test_email_normalized(self):
        user = User.objects.create_user(
            email="Test.User@Example.COM",
            password="StrongP@ss1",
        )
        # email is stored normalized (lowercased domain)
        assert user.email == "Test.User@example.com"

    def test_create_user_no_email_raises(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="super@x.com",
            password="StrongP@ss1",
        )
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.is_active is True
        assert user.is_email_verified is True

    def test_has_module_right(self, individual_role):
        user = UserFactory(role=individual_role)
        ModuleRight.objects.create(role=individual_role, module="assessment", action="view")
        assert user.has_module_right("assessment", "view") is True
        assert user.has_module_right("assessment", "delete") is False
        assert user.has_module_right("accounts", "view") is False

    def test_has_perm_superuser_bypass(self):
        user = User.objects.create_superuser(email="su@x.com", password="StrongP@ss1")
        assert user.has_perm("anything.anything") is True

    def test_str(self):
        user = UserFactory(email="str@x.com")
        assert str(user) == "str@x.com"


@pytest.mark.django_db
class TestRoleModel:
    def test_str_system_role(self):
        """System roles use the label from ROLE_CHOICES."""
        role = RoleFactory(name="individual", is_system=True)
        assert "Individual" in str(role)

    def test_str_custom_role(self):
        """Custom roles use their name directly."""
        role = RoleFactory(name="Senior Reviewer", is_system=False)
        assert str(role) == "Senior Reviewer"

    def test_unique_name(self):
        RoleFactory(name="individual")
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            RoleFactory(name="individual")


@pytest.mark.django_db
class TestUserProfileModel:
    def test_one_to_one(self):
        user = UserFactory()
        profile = UserProfileFactory(user=user)
        assert profile.user_id == user.id
        assert user.profile.id == profile.id

    def test_str(self):
        user = UserFactory(email="profile@x.com")
        profile = UserProfileFactory(user=user)
        assert "profile@x.com" in str(profile)


@pytest.mark.django_db
class TestEmailVerificationToken:
    def test_create_sets_expiry(self):
        user = UserFactory()
        token = EmailVerificationToken.objects.create(user=user)
        assert token.expires_at > timezone.now()

    def test_is_valid_unused(self):
        user = UserFactory()
        token = EmailVerificationToken.objects.create(user=user)
        assert token.is_valid is True

    def test_is_invalid_after_use(self):
        user = UserFactory()
        token = EmailVerificationToken.objects.create(user=user)
        token.used_at = timezone.now()
        token.save()
        assert token.is_valid is False

    def test_is_invalid_after_expiry(self):
        user = UserFactory()
        token = EmailVerificationToken.objects.create(user=user)
        token.expires_at = timezone.now() - timedelta(hours=1)
        token.save()
        assert token.is_valid is False


@pytest.mark.django_db
class TestPasswordResetToken:
    def test_create_sets_expiry(self):
        user = UserFactory()
        token = PasswordResetToken.objects.create(user=user)
        # 1 hour expiry
        delta = token.expires_at - timezone.now()
        assert timedelta(minutes=59) < delta < timedelta(minutes=61)

    def test_is_valid_logic(self):
        user = UserFactory()
        token = PasswordResetToken.objects.create(user=user)
        assert token.is_valid is True
        token.used_at = timezone.now()
        token.save()
        assert token.is_valid is False


@pytest.mark.django_db
class TestModuleRight:
    def test_unique_together(self, individual_role):
        ModuleRight.objects.create(role=individual_role, module="accounts", action="view")
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            ModuleRight.objects.create(role=individual_role, module="accounts", action="view")

    def test_str(self, individual_role):
        right = ModuleRight.objects.create(role=individual_role, module="accounts", action="view")
        assert "accounts.view" in str(right)
