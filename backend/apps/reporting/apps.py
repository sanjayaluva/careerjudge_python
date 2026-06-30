"""App config for Reporting."""

from django.apps import AppConfig


class ReportingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reporting"
    verbose_name = "Reporting"
    description = "General + profiling reports, PDF generation"
