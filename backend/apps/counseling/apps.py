"""App config for Counseling."""

from django.apps import AppConfig


class CounselingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.counseling"
    verbose_name = "Counseling"
    description = "Counseling sessions and notes"
