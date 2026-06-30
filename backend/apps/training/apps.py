"""App config for Training."""

from django.apps import AppConfig


class TrainingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.training"
    verbose_name = "Training"
    description = "Training setup and assignments"
