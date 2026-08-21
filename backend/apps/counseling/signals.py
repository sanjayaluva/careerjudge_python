"""Signal handlers for the Counseling module (Report 3 Counselling).

Wires up the to-and-fro notification flow that was missing. Fires on:
  - Booking confirmed -> notify counselee (§1.13)
  - Booking cancelled  -> notify counselee + helpdesk (§1.13)
  - Followup proposed  -> notify counselee + helpdesk (§2.6)

All handlers are wrapped so a notification failure NEVER crashes the
business operation that triggered it (a broken notification should not
block a booking/cancellation). Per SRS the Help Desk role is a recipient
of booking/cancellation/followup notifications.
"""

import logging
from datetime import datetime

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.models import notify_role, notify_user

from .models import CounselingSession, FollowupSession, SessionCancellation

logger = logging.getLogger(__name__)


def _fmt_dt(value) -> str:
    """Format a datetime-or-ISO-string for display; never raises."""
    if not value:
        return "(unscheduled)"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    try:
        return value.strftime("%Y-%m-%d %H:%M")
    except (AttributeError, TypeError):
        return str(value)


@receiver(post_save, sender=CounselingSession)
def _notify_on_session_status_change(sender, instance, created, **kwargs):
    """When a session moves to confirmed, notify the counselee (§1.13).

    Booking creation is handled by the view directly. Only fire on updates
    (created=False) to avoid duplicate notifications.
    """
    if created:
        return
    try:
        if instance.status == "confirmed":
            notify_user(
                instance.counselee,
                f"Session confirmed: {instance.counsellor.full_name}",
                f"Your counselling session on {_fmt_dt(instance.timeslot.start_time)} "
                f"has been confirmed by the counsellor.",
                "session",
                f"/counseling?session={instance.id}",
            )
    except Exception as e:
        logger.warning("Counseling confirm notification failed: %s", e)


@receiver(post_save, sender=SessionCancellation)
def _notify_on_cancellation(sender, instance, created, **kwargs):
    """Report 3 §1.13: on cancellation, notify the counselee + helpdesk."""
    if not created:
        return
    try:
        session = instance.session
        refund_label = instance.get_refund_tier_display()
        notify_user(
            session.counselee,
            f"Session cancelled: {session.counsellor.full_name}",
            f"Your session has been cancelled ({instance.get_cancelled_by_display()}). "
            f"Refund: {refund_label}. You may book another timeslot with this or another "
            f"counsellor.",
            "warning",
            "/counseling",
        )
        notify_role(
            "helpdesk",
            f"Session cancelled: {session.counselee.email}",
            f"Session #{session.id} between {session.counselee.email} and "
            f"{session.counsellor.full_name} was cancelled ({refund_label}).",
            "session",
        )
    except Exception as e:
        logger.warning("Counseling cancellation notification failed: %s", e)


@receiver(post_save, sender=FollowupSession)
def _notify_on_followup(sender, instance, created, **kwargs):
    """Report 3 §2.6: when a followup is proposed, notify counselee + helpdesk."""
    if not created:
        return
    try:
        session = instance.original_session
        proposed_str = _fmt_dt(instance.proposed_time)
        notify_user(
            session.counselee,
            f"Follow-up session proposed: {session.counsellor.full_name}",
            f"Your counsellor proposed a follow-up on {proposed_str}. Please book and "
            f"complete payment to confirm.",
            "session",
            "/counseling",
        )
        notify_role(
            "helpdesk",
            f"Follow-up proposed: {session.counselee.email}",
            f"A follow-up was proposed for {session.counselee.email} with "
            f"{session.counsellor.full_name} on {proposed_str}.",
            "session",
        )
    except Exception as e:
        logger.warning("Counseling followup notification failed: %s", e)
