"""App config for Messaging."""

from django.apps import AppConfig


class MessagingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.messaging"
    verbose_name = "Messaging"
    description = "Live-chat messaging between roles (Doc 4)"
