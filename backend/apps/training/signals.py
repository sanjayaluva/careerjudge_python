"""Signal handlers for the Training module.

Wires up:
  - LiveSession created/scheduled → notify all registered students
  - Student consents to live session → notify the trainer
"""

from datetime import datetime

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.models import notify_user

from .models import CourseRegistration, LiveSession, LiveSessionConsent


def _parse_datetime(value):
    """Parse a datetime that might be a string (ORM create) or datetime."""
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


@receiver(post_save, sender=LiveSession)
def notify_students_of_live_session(sender, instance, created, **kwargs):
    """When a live session is created or updated to 'scheduled', notify
    all registered (paid) students of the course (SRS §5).

    The notification link includes the live_session ID so the frontend
    can show the consent modal: /training/<course_id>?live_session=<id>
    """
    if instance.status != "scheduled":
        return
    # Only notify on creation, not every save (avoid spam on edits)
    if not created:
        return

    regs = CourseRegistration.objects.filter(
        course=instance.course,
        payment_status="paid",
    ).select_related("student")

    scheduled = _parse_datetime(instance.scheduled_at)
    scheduled_str = scheduled.strftime("%Y-%m-%d %H:%M")
    for reg in regs:
        notify_user(
            reg.student,
            f"Live session scheduled: {instance.title}",
            f"Scheduled for {scheduled_str}. Duration: {instance.duration_minutes} min. "
            f"Mode: {instance.mode}.",
            "session",
            f"/training/{instance.course_id}?live_session={instance.id}",
        )


@receiver(post_save, sender=LiveSessionConsent)
def notify_trainer_of_consent(sender, instance, created, **kwargs):
    """When a student consents/declines, notify the course trainer (SRS §5).

    Per SRS: 'notification goes back to trainer about student participation.'
    """
    if not created:
        return  # Only notify on first consent, not updates

    trainer = instance.live_session.course.created_by
    if not trainer:
        return

    student_name = instance.student.full_name or instance.student.email
    status_label = "consented to attend" if instance.status == "consented" else "declined"
    scheduled = _parse_datetime(instance.live_session.scheduled_at)
    notify_user(
        trainer,
        f"{student_name} {status_label}",
        f"Live session: {instance.live_session.title} on " f"{scheduled:%Y-%m-%d %H:%M}",
        "session",
        f"/training/{instance.live_session.course_id}",
    )
