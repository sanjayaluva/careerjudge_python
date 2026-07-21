"""App config for Training."""

from django.apps import AppConfig


class TrainingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.training"
    verbose_name = "Training"
    description = "Training setup and assignments"

    def ready(self):
        # Import signal handlers so they're registered on app load
        from . import signals  # noqa: F401
