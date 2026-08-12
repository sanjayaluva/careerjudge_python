"""App config for Counseling."""

from django.apps import AppConfig


class CounselingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.counseling"
    verbose_name = "Counseling"
    description = "Counseling sessions and notes"

    def ready(self):
        # Report 3: import signal handlers so the to-and-fro notification
        # flow (booking -> confirm/cancel -> followup) is wired up.
        from . import signals  # noqa: F401
