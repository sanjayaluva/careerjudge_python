"""Business logic for the accounts module.

Keeping heavy logic out of views and serializers makes the code easier to test
and reuse. Views call these service functions.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import (
    EmailVerificationToken,
    ModuleRight,
    PasswordResetToken,
    Role,
    User,
)

# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


def create_email_verification_token(user: User) -> EmailVerificationToken:
    """Create a fresh verification token (24h expiry) for the user."""
    # invalidate previous unused tokens
    EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    token = EmailVerificationToken.objects.create(user=user)
    return token


def send_verification_email(user: User, token: EmailVerificationToken) -> None:
    """Send the activation link email. In dev, this prints to console."""
    verification_url = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email/{token.token}"
    send_mail(
        subject="CareerJudge — Verify your email",
        message=(
            f"Welcome to CareerJudge!\n\n"
            f"Please verify your email by clicking the link below:\n"
            f"{verification_url}\n\n"
            f"This link expires in 24 hours.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@transaction.atomic
def verify_email(token: EmailVerificationToken) -> User:
    """Mark the user's email as verified and activate the account."""
    user = token.user
    user.is_email_verified = True
    user.is_active = True
    user.save(update_fields=["is_email_verified", "is_active", "updated_at"])
    token.used_at = timezone.now()
    token.save(update_fields=["used_at"])
    return user


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


def create_password_reset_token(user: User) -> PasswordResetToken:
    """Create a fresh password reset token (1h expiry) for the user."""
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    return PasswordResetToken.objects.create(user=user)


def send_password_reset_email(user: User, token: PasswordResetToken) -> None:
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password/{token.token}"
    send_mail(
        subject="CareerJudge — Password reset",
        message=(
            f"Hello {user.full_name or 'user'},\n\n"
            f"We received a request to reset your password. Click below:\n"
            f"{reset_url}\n\n"
            f"This link expires in 1 hour. If you did not request this, "
            f"please ignore this email.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@transaction.atomic
def reset_password(token: PasswordResetToken, new_password: str) -> User:
    user = token.user
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    token.used_at = timezone.now()
    token.save(update_fields=["used_at"])
    return user


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------


def get_or_create_default_roles() -> dict[str, Role]:
    """Idempotently create the 10 system roles. Returns name → Role map.

    System roles are marked is_system=True and is_frozen=True — their
    permissions cannot be modified after creation.
    """
    roles: dict[str, Role] = {}
    for code, label in Role.ROLE_CHOICES:
        role, _created = Role.objects.get_or_create(
            name=code,
            defaults={
                "description": label,
                "is_system": True,
                "is_frozen": True,
            },
        )
        # If role already existed but wasn't marked as system (migration scenario),
        # update it.
        if not role.is_system:
            role.is_system = True
            role.is_frozen = True
            role.save(update_fields=["is_system", "is_frozen", "updated_at"])
        roles[code] = role
    return roles


def assign_role_to_user(user: User, role_name: str) -> Role:
    """Assign a role to a user. Raises Role.DoesNotExist if invalid."""
    role = Role.objects.get(name=role_name)
    user.role = role
    user.save(update_fields=["role", "updated_at"])
    return role


def assign_permission_to_role(role: "Role", module: str, action: str) -> "ModuleRight":
    """Additively grant a permission to a role.

    For frozen roles, this is the ONLY allowed mutation (additive grant).
    Removals are forbidden — see MODULE_FREEZE.md.
    """
    right, _ = ModuleRight.objects.get_or_create(role=role, module=module, action=action)
    return right
