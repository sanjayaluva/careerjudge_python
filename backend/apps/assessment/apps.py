"""App config for Assessment."""
from django.apps import AppConfig


class AssessmentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assessment"
    verbose_name = "Assessment"
    description = "Sessions, attempts, 8 scoring modes"
