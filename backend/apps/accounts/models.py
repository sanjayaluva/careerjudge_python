"""Models for the accounts module.

Spec source: 11_SRS.json (UC001-UC007, UC018, UC043),
              09_admin_system_administration.json

All roles (9):
    cj_admin, corp_admin, corp_exclusive, psychometrician, sme_reviewer,
    trainer, group_admin, counsellor, individual
"""

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# ---------------------------------------------------------------------------
# User manager
# ---------------------------------------------------------------------------


class UserManager(BaseUserManager):
    """Custom manager using email as the unique identifier."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", False)  # requires email verification
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


# ---------------------------------------------------------------------------
# Role & permissions
# ---------------------------------------------------------------------------


class Role(models.Model):
    """Named role — e.g. 'cj_admin', 'corp_admin', 'individual'.

    A role groups a set of module-specific action rights. Per business rule
    (UC018): 'Once a role is created with appropriate privileges, those
    privileges should not be modified in the future.' We enforce this at the
    application layer (frozen roles can only receive additional permissions,
    never removals).

    SME vs Reviewer (split per client clarification 2026-06-30):
      - sme:      Creates / views / edits / deletes OWN questions
                  (only while unreviewed; once reviewed, cannot edit/delete
                  directly — must request admin deletion).
      - reviewer: Reviews questions submitted by SMEs. Cannot create/edit/
                  delete questions. Can approve/reject.
    """

    ROLE_CHOICES = [
        ("cj_admin", "CareerJudge Admin"),
        ("corp_admin", "Corporate Admin"),
        ("corp_exclusive", "Corporate Exclusive"),
        ("psychometrician", "Psychometrician"),
        ("sme", "SME (Subject Matter Expert)"),
        ("reviewer", "Reviewer"),
        ("trainer", "Trainer"),
        ("group_admin", "Group Admin"),
        ("counsellor", "Counsellor"),
        ("individual", "Individual"),
    ]

    name = models.CharField(_("name"), max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(_("description"), blank=True)
    is_frozen = models.BooleanField(
        _("frozen"),
        default=False,
        help_text=_("Frozen roles accept additive permission grants only."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("role")
        verbose_name_plural = _("roles")

    def __str__(self) -> str:
        return self.get_name_display()


class ModuleRight(models.Model):
    """Action-wise permission per module.

    Each row says: role X has action Y on module Z.
    Action codenames follow the Django auth convention: view, add, change, delete,
    plus custom actions like 'approve', 'assign', 'export', 'generate_report'.
    """

    ACTION_CHOICES = [
        ("view", "View"),
        ("add", "Add"),
        ("change", "Change"),
        ("delete", "Delete"),
        ("approve", "Approve"),
        ("reject", "Reject"),
        ("review", "Review"),
        ("assign", "Assign"),
        ("export", "Export"),
        ("generate_report", "Generate Report"),
        ("request_delete", "Request Deletion"),
    ]

    MODULE_CHOICES = [
        ("accounts", "Accounts"),
        ("organizations", "Organizations"),
        ("question_bank", "Question Bank"),
        ("assessment", "Assessment"),
        ("career_profiling", "Career Profiling"),
        ("reporting", "Reporting"),
        ("training", "Training"),
        ("counseling", "Counseling"),
        ("cms", "CMS"),
        ("notifications", "Notifications"),
    ]

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="rights")
    module = models.CharField(_("module"), max_length=50, choices=MODULE_CHOICES)
    action = models.CharField(_("action"), max_length=50, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["module", "action"]
        unique_together = [("role", "module", "action")]
        verbose_name = _("module right")
        verbose_name_plural = _("module rights")

    def __str__(self) -> str:
        return f"{self.role.name}: {self.module}.{self.action}"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(AbstractUser):
    """Custom user — email-based, no username.

    Per UC001:
    - Signup creates an inactive user with is_email_verified=False.
    - Activation link sent via email with single-use token.
    - On verification, is_active=True and is_email_verified=True.
    """

    username = None  # remove username field
    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(_("full name"), max_length=255, blank=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
        help_text=_(
            "Primary role for this user. Additional module-specific " "rights via ModuleRight."
        ),
    )
    is_email_verified = models.BooleanField(
        _("email verified"),
        default=False,
        help_text=_("Whether the user has verified their email via activation link."),
    )
    phone = models.CharField(_("phone"), max_length=20, blank=True)
    is_trial_user = models.BooleanField(
        _("trial user"),
        default=False,
        help_text=_("Whether this user is on a trial plan."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        return self.full_name or self.email

    def get_short_name(self) -> str:
        return self.full_name.split()[0] if self.full_name else self.email

    # --- Permission helpers ---

    def has_module_right(self, module: str, action: str) -> bool:
        """Check if user has a specific module right via their role."""
        if not self.role_id:
            return False
        return ModuleRight.objects.filter(
            role_id=self.role_id, module=module, action=action
        ).exists()

    def has_perm(self, perm, obj=None):
        """Override Django's has_perm to use module rights.

        perm is in the form '<module>.<action>' (e.g. 'accounts.view_user').
        """
        if self.is_superuser:
            return True
        if "." in perm:
            app_label, codename = perm.split(".", 1)
            return self.has_module_right(app_label, codename)
        return super().has_perm(perm, obj)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class UserProfile(models.Model):
    """Extended profile fields per UC005 (Manage Profile).

    Fields beyond the User model that are personal/biographical.
    """

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("non_binary", "Non-binary"),
        ("prefer_not_to_say", "Prefer not to say"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    gender = models.CharField(_("gender"), max_length=20, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(_("date of birth"), null=True, blank=True)
    mobile = models.CharField(_("mobile"), max_length=15, blank=True)
    avatar = models.ImageField(_("avatar"), upload_to="avatars/", null=True, blank=True)
    address_line1 = models.CharField(_("address line 1"), max_length=255, blank=True)
    address_line2 = models.CharField(_("address line 2"), max_length=255, blank=True)
    city = models.CharField(_("city"), max_length=100, blank=True)
    state = models.CharField(_("state"), max_length=100, blank=True)
    country = models.CharField(_("country"), max_length=100, blank=True)
    postal_code = models.CharField(_("postal code"), max_length=20, blank=True)
    bio = models.TextField(_("bio"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self) -> str:
        return f"Profile of {self.user.email}"


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


class EmailVerificationToken(models.Model):
    """Single-use token for email verification (UC001)."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_verification_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"EmailVerificationToken({self.user.email}, {self.token})"

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from datetime import timedelta

            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)


class PasswordResetToken(models.Model):
    """Single-use token for password reset."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PasswordResetToken({self.user.email}, {self.token})"

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from datetime import timedelta

            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)
