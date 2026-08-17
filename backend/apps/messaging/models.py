"""Models for the Messaging module.

Per Doc 4: Live-chat messaging system between roles.
8 roles need this: Corp Admin, Group Admin, Corp Excl Admin,
Channel Partner, SME, Reviewer, Trainer, Counsellor.

Messages are between two users. A conversation is a pair of users.
Messages have sender, recipient, subject, body, read/unread.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Message(models.Model):
    """A single message from one user to another.

    Supports role-to-role messaging (e.g., SME → CJ Admin, Trainer → Helpdesk).
    Conversations are identified by the (sender, recipient) pair.
    """

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    subject = models.CharField(_("subject"), max_length=255, blank=True, default="")
    body = models.TextField(_("body"))
    is_read = models.BooleanField(_("read"), default=False)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
        help_text=_("If this is a reply, points to the original message."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        indexes = [
            models.Index(fields=["sender", "recipient"]),
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"{self.sender.email} → {self.recipient.email}: {self.subject or self.body[:50]}"


class Conversation(models.Model):
    """A conversation thread between two users.

    A conversation is created when the first message is sent between
    a pair of users. Subsequent messages between the same pair are
    linked to the same conversation.
    """

    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations_as_user1",
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations_as_user2",
    )
    last_message_at = models.DateTimeField(_("last message at"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user1", "user2")]
        ordering = ["-last_message_at"]
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")

    def __str__(self) -> str:
        return f"Conversation: {self.user1.email} ↔ {self.user2.email}"

    @property
    def other_user(self):
        """Helper to get the other user in the conversation."""
        return self.user2  # caller should check which user they are

    def get_other_user(self, current_user):
        """Get the other user in the conversation relative to current_user."""
        return self.user2 if current_user.id == self.user1_id else self.user1
