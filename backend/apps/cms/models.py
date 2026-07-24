"""Models for the CMS module.

Provides content management for:
  - Pages: static content pages (About, Privacy Policy, Terms, etc.)
  - Banners: homepage banners / promotional content
  - Menu items: navigation menu links

All content supports draft/published states and ordering.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Page(models.Model):
    """A static content page (About, Privacy, Terms, etc.)."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(_("title"), max_length=255)
    slug = models.SlugField(
        _("slug"), max_length=255, unique=True, help_text=_("URL path, e.g., 'about'")
    )
    body = models.TextField(_("body"), help_text=_("HTML or markdown content"))
    meta_description = models.CharField(
        _("meta description"), max_length=500, blank=True, default=""
    )
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="draft")
    order = models.PositiveIntegerField(_("display order"), default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cms_pages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = _("page")
        verbose_name_plural = _("pages")

    def __str__(self) -> str:
        return self.title


class Banner(models.Model):
    """A homepage banner / promotional content block."""

    POSITION_CHOICES = [
        ("hero", "Hero (top of homepage)"),
        ("sidebar", "Sidebar"),
        ("footer", "Footer"),
        ("inline", "Inline (between content)"),
    ]

    title = models.CharField(_("title"), max_length=255)
    subtitle = models.CharField(_("subtitle"), max_length=500, blank=True, default="")
    body = models.TextField(_("body"), blank=True, default="", help_text=_("HTML or text content"))
    image = models.TextField(
        _("image"), blank=True, default="", help_text=_("URL or base64 data URL")
    )
    link_url = models.URLField(
        _("link URL"), blank=True, default="", help_text=_("Click-through URL")
    )
    link_text = models.CharField(_("link text"), max_length=100, blank=True, default="Learn more")
    position = models.CharField(
        _("position"), max_length=20, choices=POSITION_CHOICES, default="hero"
    )
    is_active = models.BooleanField(_("active"), default=True)
    order = models.PositiveIntegerField(_("display order"), default=0)
    starts_at = models.DateTimeField(_("starts at"), null=True, blank=True)
    ends_at = models.DateTimeField(_("ends at"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cms_banners",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = _("banner")
        verbose_name_plural = _("banners")

    def __str__(self) -> str:
        return self.title


class MenuItem(models.Model):
    """A navigation menu item (header or footer links)."""

    LOCATION_CHOICES = [
        ("header", "Header"),
        ("footer", "Footer"),
        ("sidebar", "Sidebar"),
    ]

    label = models.CharField(_("label"), max_length=100)
    url = models.CharField(_("URL"), max_length=500, help_text=_("Internal path or external URL"))
    location = models.CharField(
        _("location"), max_length=20, choices=LOCATION_CHOICES, default="header"
    )
    order = models.PositiveIntegerField(_("display order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)
    opens_new_tab = models.BooleanField(_("opens in new tab"), default=False)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text=_("Parent menu item for dropdowns"),
    )

    class Meta:
        ordering = ["location", "order"]
        verbose_name = _("menu item")
        verbose_name_plural = _("menu items")

    def __str__(self) -> str:
        return f"{self.location}: {self.label}"
