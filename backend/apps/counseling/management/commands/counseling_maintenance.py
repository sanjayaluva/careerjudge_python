"""Counseling maintenance jobs (Report 3 §1.3, §1.12).

Runs the two periodic checks the report requires:

  1. Slot-coverage check (§1.3): every counsellor must always have at least
     one week of available timeslots. If not, notify the counsellor to
     update their slots + notify the helpdesk so they can follow up.

  2. Confirm-window auto-cancel (§1.12): a pending booking the counsellor
     has not confirmed within confirm_window_hours (default 6) is
     auto-cancelled; the counselee is notified and asked to rebook.

Recommended cron: hourly.

Usage:
    python manage.py counseling_maintenance            # run both checks
    python manage.py counseling_maintenance --slots    # only slot coverage
    python manage.py counseling_maintenance --confirm  # only confirm window
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.counseling.models import CounselingSession, CounselingSettings, CounsellorProfile
from apps.notifications.models import notify_role, notify_user


class Command(BaseCommand):
    help = "Counseling maintenance: slot-coverage reminders + confirm-window auto-cancel."

    def add_arguments(self, parser):
        parser.add_argument("--slots", action="store_true", help="Only run the slot check")
        parser.add_argument("--confirm", action="store_true", help="Only run the confirm check")

    def handle(self, *args, **options):
        run_slots = options["slots"] or not (options["slots"] or options["confirm"])
        run_confirm = options["confirm"] or not (options["slots"] or options["confirm"])

        if run_slots:
            self._check_slot_coverage()
        if run_confirm:
            self._auto_cancel_unconfirmed()

    def _check_slot_coverage(self):
        """§1.3: notify counsellors with <1 week of available slots + helpdesk."""
        settings = CounselingSettings.get()
        horizon = timezone.now() + timedelta(weeks=1)
        short = []
        for counsellor in CounsellorProfile.objects.select_related("user"):
            has_near_term = counsellor.timeslots.filter(
                status="available", start_time__gte=timezone.now(), start_time__lte=horizon
            ).exists()
            if not has_near_term:
                short.append(counsellor)
                notify_user(
                    counsellor.user,
                    "Timeslot update needed",
                    "You have less than one week of available timeslots. Please add "
                    "more so candidates can book (max "
                    f"{settings.max_weeks_ahead} weeks ahead).",
                    "warning",
                    "/counseling",
                )
        if short:
            names = ", ".join(c.full_name for c in short)
            notify_role(
                "helpdesk",
                "Counsellor slot shortage",
                f"{len(short)} counsellor(s) have less than one week of slots: {names}. "
                "Please remind them to update their availability.",
                "warning",
            )
        self.stdout.write(f"Slot coverage: {len(short)} counsellor(s) short of slots.")

    def _auto_cancel_unconfirmed(self):
        """§1.12: auto-cancel pending bookings past the confirm window."""
        settings = CounselingSettings.get()
        cutoff = timezone.now() - timedelta(hours=settings.confirm_window_hours)
        stale = CounselingSession.objects.filter(
            status="pending", booked_at__lte=cutoff
        ).select_related("counselee", "counsellor", "counsellor__user", "timeslot")
        count = 0
        for session in stale:
            session.status = "cancelled"
            session.save(update_fields=["status"])
            # Free the timeslot for rebooking.
            if session.timeslot_id:
                session.timeslot.status = "available"
                session.timeslot.save(update_fields=["status"])
            notify_user(
                session.counselee,
                "Booking expired: counsellor did not confirm",
                f"Your booking with {session.counsellor.full_name} was not confirmed within "
                f"{settings.confirm_window_hours} hours and has been cancelled. "
                "Please book another timeslot with this or another counsellor.",
                "warning",
                "/counseling",
            )
            count += 1
        self.stdout.write(f"Confirm window: auto-cancelled {count} stale booking(s).")
