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
