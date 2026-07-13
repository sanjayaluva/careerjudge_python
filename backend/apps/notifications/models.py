"""Models for the Notifications module.

Provides a flexible notification system that can be triggered by any
part of the application (question submitted for review, assessment
published, session completed, etc.).

Notifications are per-user — each user sees only their own notifications.
Each notification has a type, message, optional link, and read/unread state.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """A notification message for a specific user.

    Created by system events (signals, view code, or explicit calls to
    notify_user / notify_role). Displayed in the bell-icon dropdown.
    """

    TYPE_CHOICES = [
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("review", "Review Requested"),
        ("assessment", "Assessment Update"),
        ("session", "Session Update"),
        ("system", "System"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        _("type"), max_length=20, choices=TYPE_CHOICES, default="info"
    )
    title = models.CharField(_("title"), max_length=255)
    message = models.TextField(_("message"))
    """Optional URL the user can navigate to when clicking the notification."""
    link = models.CharField(_("link"), max_length=500, blank=True, default="")
    is_read = models.BooleanField(_("read"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.recipient.email}: {self.title[:50]}"

    def mark_as_read(self):
        """Mark this notification as read."""
        from django.utils import timezone

        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


# ---------------------------------------------------------------------------
# Helper functions for creating notifications
# ---------------------------------------------------------------------------


def notify_user(user, title, message, notification_type="info", link=""):
    """Create a notification for a single user.

    Usage:
        from apps.notifications.models import notify_user
        notify_user(reviewer, "New question to review", "Question 'X' is pending content review.", "review", "/question-bank/42")
    """
    return Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )


def notify_role(role_name, title, message, notification_type="info", link=""):
    """Create a notification for all users with the given role.

    Usage:
        from apps.notifications.models import notify_role
        notify_role("reviewer", "New questions pending", "3 questions are pending content review.", "review")
    """
    from apps.accounts.models import Role

    try:
        role = Role.objects.get(name=role_name)
    except Role.DoesNotExist:
        return []
    users = role.users.filter(is_active=True)
    return [
        Notification.objects.create(
            recipient=u,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )
        for u in users
    ]
