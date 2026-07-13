"""App config for Notifications."""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"
    description = "In-app notifications for system events"

    def ready(self):
        """Import signal handlers when the app is ready."""
        from . import signals  # noqa: F401
