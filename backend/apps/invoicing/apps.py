"""App config for Invoicing."""

from django.apps import AppConfig


class InvoicingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.invoicing"
    verbose_name = "Invoicing"
    description = "Invoice management for empanelled users (Doc 4)"
