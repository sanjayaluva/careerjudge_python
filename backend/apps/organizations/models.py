"""Models for the organizations module.

Multi-tenancy foundation — links users to corporate entities.

Organization types (inferred from SRS roles):
  - corporate: standard corporate entity (managed by corp_admin)
  - corp_exclusive: exclusive corporate entity (managed by corp_exclusive)
  - channel_partner: channel partner entity (managed by channel partner role)

Groups are sub-entities within an organization (managed by group_admin).
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Organization(models.Model):
    """Corporate entity — a company or organization that uses CareerJudge.

    Types:
      - corporate: standard corporate (corp_admin manages users)
      - corp_exclusive: exclusive corporate (corp_exclusive manages users)
      - channel_partner: channel partner (manages their own users)
    """

    TYPE_CHOICES = [
        ("corporate", "Corporate"),
        ("corp_exclusive", "Corporate Exclusive"),
        ("channel_partner", "Channel Partner"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("suspended", "Suspended"),
    ]

    name = models.CharField(_("name"), max_length=255, unique=True)
    type = models.CharField(_("type"), max_length=50, choices=TYPE_CHOICES, default="corporate")
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="active")
    description = models.TextField(_("description"), blank=True)
    # Doc 9 §2.2 onboarding fields: primary-contact manager + tax identifier.
    manager_name = models.CharField(
        _("manager name"),
        max_length=255,
        blank=True,
        help_text=_("Name of the primary-contact manager (Doc 9 §2.2)."),
    )
    tax_id = models.CharField(
        _("PAN/TAN"),
        max_length=40,
        blank=True,
        help_text=_("PAN/TAN of the organization (Doc 9 §2.2)."),
    )
    contact_email = models.EmailField(_("contact email"), blank=True)
    contact_phone = models.CharField(_("contact phone"), max_length=20, blank=True)
    website = models.URLField(_("website"), blank=True)
    address_line1 = models.CharField(_("address line 1"), max_length=255, blank=True)
    address_line2 = models.CharField(_("address line 2"), max_length=255, blank=True)
    city = models.CharField(_("city"), max_length=100, blank=True)
    state = models.CharField(_("state"), max_length=100, blank=True)
    country = models.CharField(_("country"), max_length=100, blank=True)
    postal_code = models.CharField(_("postal code"), max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")

    def __str__(self) -> str:
        return self.name


class Group(models.Model):
    """Sub-group within an organization — managed by group_admin role."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(_("name"), max_length=255)
    # CJ_UC052: a corporate group carries a Region/Division.
    region_division = models.CharField(
        _("region/division"),
        max_length=100,
        blank=True,
        help_text=_("Region or division of the corporate (CJ_UC052)."),
    )
    description = models.TextField(_("description"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]
        verbose_name = _("group")
        verbose_name_plural = _("groups")

    def __str__(self) -> str:
        return f"{self.organization.name} — {self.name}"


class OrganizationMember(models.Model):
    """Links a user to an organization (and optionally a group).

    A user can be a member of one organization. The group is optional.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="organization_memberships"
    )
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, related_name="members", null=True, blank=True
    )
    # Doc 9 §2.3: a corporate individual is onboarded with an Employee ID.
    employee_id = models.CharField(_("employee ID"), max_length=50, blank=True)
    is_admin = models.BooleanField(
        _("is admin"),
        default=False,
        help_text=_("Whether this member is an admin of the organization."),
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-joined_at"]
        unique_together = [("organization", "user")]
        verbose_name = _("organization member")
        verbose_name_plural = _("organization members")

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.organization.name}"


# ---------------------------------------------------------------------------
# DomainCategory — for tagging SME/Reviewer to domain expertise areas
# Per Doc 4 CJ Admin Issues 5-7: SME/Reviewer tagged to domain categories
# ---------------------------------------------------------------------------


class DomainCategory(models.Model):
    """A domain expertise category (e.g. Mathematics, Physics, Chemistry).

    SMEs and Reviewers are tagged to domain categories so that questions
    created by an SME in a domain reach a Reviewer with the same domain
    expertise. Per Doc 4 CJ Admin Issues 5, 6, 7.
    """

    name = models.CharField(_("name"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("domain category")
        verbose_name_plural = _("domain categories")

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# OrganizationAssignment — CJ Admin assigns assessments/training courses
# to organizations. Per Doc 4 CJ Admin Issues 12-14, 17-18.
# ---------------------------------------------------------------------------


class OrganizationAssignment(models.Model):
    """Links a published assessment or training course to an organization.

    CJ Admin selects specific published assessments/training courses and
    assigns them to a Corp organization or channel partner. Only assigned
    items are visible to the org's users.
    """

    ITEM_TYPE_CHOICES = [
        ("assessment", "Assessment"),
        ("training_course", "Training Course"),
        ("counseling", "Counseling Service"),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="assignments"
    )
    item_type = models.CharField(_("item type"), max_length=20, choices=ITEM_TYPE_CHOICES)
    item_id = models.PositiveIntegerField(_("item ID"))
    assigned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="org_assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assigned_at"]
        unique_together = [("organization", "item_type", "item_id")]
        verbose_name = _("organization assignment")
        verbose_name_plural = _("organization assignments")

    def __str__(self) -> str:
        return f"{self.organization.name} → {self.item_type}#{self.item_id}"


# ---------------------------------------------------------------------------
# AssessmentSchedule (CJ_UC053) — a corporate/group admin schedules an
# assessment for their employees at a date/time; members are notified.
# ---------------------------------------------------------------------------


class AssessmentSchedule(models.Model):
    """A scheduled assessment for a corporate's employees (CJ_UC053).

    Scoped to an organization (and optionally a single group). On creation the
    targeted members are notified. The assessment is referenced by FK to
    ``assessment.Assessment`` (string ref avoids an import cycle).
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="assessment_schedules"
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        related_name="assessment_schedules",
        null=True,
        blank=True,
        help_text=_("Optional — schedule for one group only; NULL = whole organization."),
    )
    assessment = models.ForeignKey(
        "assessment.Assessment", on_delete=models.CASCADE, related_name="schedules"
    )
    scheduled_at = models.DateTimeField(_("scheduled at"))
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="created_schedules"
    )
    notified = models.BooleanField(_("members notified"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]
        verbose_name = _("assessment schedule")
        verbose_name_plural = _("assessment schedules")

    def __str__(self) -> str:
        return f"{self.organization.name} → assessment#{self.assessment_id} @ {self.scheduled_at}"


# ---------------------------------------------------------------------------
# CorporateWebsite (CJ_UC054 + CJ_UC055) — a per-corporate branded portal.
#
# Logical multi-tenancy (Option B, see docs/compliance/corporate_exclusive_scope
# .md §4): each Corporate-Exclusive gets its own slug/subdomain, branding, and a
# generated corporate-admin login. Data isolation is by organization membership
# (see scoping.py), NOT a physically separate database. DNS/subdomain wiring is
# an ops step; the app resolves a tenant by its ``slug``.
# ---------------------------------------------------------------------------


class CorporateWebsite(models.Model):
    """A branded portal for one corporate (CJ_UC054 customization + CJ_UC055)."""

    LAYOUT_CHOICES = [
        ("classic", "Classic"),
        ("modern", "Modern"),
        ("minimal", "Minimal"),
    ]

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="corporate_website"
    )
    slug = models.SlugField(_("slug"), max_length=63, unique=True)
    company_name = models.CharField(_("company name"), max_length=255)
    logo_url = models.CharField(_("logo URL"), max_length=1000, blank=True)
    layout = models.CharField(_("layout"), max_length=20, choices=LAYOUT_CHOICES, default="classic")
    primary_color = models.CharField(_("primary color"), max_length=9, default="#4f46e5")
    admin_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="administered_websites",
        help_text=_("The generated corporate-admin account for this website (CJ_UC055)."),
    )
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("corporate website")
        verbose_name_plural = _("corporate websites")

    def __str__(self) -> str:
        return f"{self.company_name} ({self.slug})"
