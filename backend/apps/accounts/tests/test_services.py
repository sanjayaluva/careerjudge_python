"""Tests for accounts services (business logic layer)."""

import pytest
from django.utils import timezone

from apps.accounts.models import (
    ModuleRight,
    Role,
)
from apps.accounts.services import (
    assign_permission_to_role,
    assign_role_to_user,
    create_email_verification_token,
    create_password_reset_token,
    get_or_create_default_roles,
)
from apps.accounts.services import (
    reset_password as svc_reset_password,
)
from apps.accounts.services import (
    verify_email as svc_verify_email,
)

from .factories import RoleFactory, UserFactory


@pytest.mark.django_db
class TestCreateEmailVerificationToken:
    def test_creates_token(self):
        user = UserFactory()
        token = create_email_verification_token(user)
        assert token.user_id == user.id
        assert token.expires_at > timezone.now()
        assert token.used_at is None

    def test_invalidates_previous_tokens(self):
        user = UserFactory()
        old_token = create_email_verification_token(user)
        new_token = create_email_verification_token(user)
        old_token.refresh_from_db()
        assert old_token.used_at is not None
        assert new_token.used_at is None


@pytest.mark.django_db
class TestVerifyEmail:
    def test_activates_user(self):
        user = UserFactory(is_active=False, is_email_verified=False)
        token = create_email_verification_token(user)
        svc_verify_email(token)
        user.refresh_from_db()
        assert user.is_active is True
        assert user.is_email_verified is True
        token.refresh_from_db()
        assert token.used_at is not None


@pytest.mark.django_db
class TestPasswordReset:
    def test_create_token(self):
        user = UserFactory()
        token = create_password_reset_token(user)
        assert token.user_id == user.id

    def test_reset_password(self):
        user = UserFactory()
        token = create_password_reset_token(user)
        svc_reset_password(token, "NewStrongP@ss5")
        user.refresh_from_db()
        assert user.check_password("NewStrongP@ss5")
        token.refresh_from_db()
        assert token.used_at is not None


@pytest.mark.django_db
class TestGetOrCreateDefaultRoles:
    def test_creates_all_9_roles(self):
        roles = get_or_create_default_roles()
        assert len(roles) == 9
        for code, _ in [("cj_admin", ""), ("individual", "")]:
            assert code in roles

    def test_idempotent(self):
        get_or_create_default_roles()
        roles = get_or_create_default_roles()
        assert len(roles) == 9


@pytest.mark.django_db
class TestAssignRoleToUser:
    def test_happy_path(self):
        user = UserFactory()
        role = RoleFactory(name="trainer")
        result = assign_role_to_user(user, "trainer")
        assert result.id == role.id
        user.refresh_from_db()
        assert user.role_id == role.id

    def test_invalid_role_raises(self):
        user = UserFactory()
        with pytest.raises(Role.DoesNotExist):
            assign_role_to_user(user, "nonexistent")


@pytest.mark.django_db
class TestAssignPermissionToRole:
    def test_creates_right(self):
        role = RoleFactory(name="individual")
        right = assign_permission_to_role(role, "accounts", "view")
        assert right.module == "accounts"
        assert right.action == "view"

    def test_idempotent(self):
        role = RoleFactory(name="individual")
        assign_permission_to_role(role, "accounts", "view")
        # second call should not duplicate
        assign_permission_to_role(role, "accounts", "view")
        assert ModuleRight.objects.filter(role=role).count() == 1
