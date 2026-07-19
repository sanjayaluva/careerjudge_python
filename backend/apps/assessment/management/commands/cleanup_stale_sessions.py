"""Management command to auto-abandon stale active sessions.

Sessions that have been 'active' for longer than the assessment's duration
(+ 1 hour grace period) are marked as 'abandoned'. This prevents stale
sessions from blocking retakes (SINGLE_SESSION rule) and keeps the
database clean.

Usage:
    python manage.py cleanup_stale_sessions

Recommended: run via cron every hour:
    0 * * * * cd /opt/careerjudge && docker compose -f infra/docker/docker-compose.dev.yml exec -T backend python manage.py cleanup_stale_sessions
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.assessment.models import AssessmentSession


class Command(BaseCommand):
    help = "Auto-abandon stale active sessions that have exceeded their time limit."

    def handle(self, *args, **options):
        now = timezone.now()
        abandoned_count = 0

        # Find all active sessions
        active_sessions = AssessmentSession.objects.filter(status="active").select_related(
            "assessment"
        )

        for session in active_sessions:
            duration = session.assessment.total_duration_seconds
            if not duration:
                # No time limit — abandon after 6 hours of inactivity
                cutoff = session.started_at + timedelta(hours=6)
            else:
                # Abandon after duration + 1 hour grace
                cutoff = session.started_at + timedelta(seconds=duration + 3600)

            if now > cutoff:
                session.status = "abandoned"
                session.completed_at = now
                session.save(update_fields=["status", "completed_at"])
                abandoned_count += 1
                self.stdout.write(
                    f"  Abandoned: Session #{session.id} "
                    f"({session.candidate.email} - {session.assessment.title})"
                )

        if abandoned_count == 0:
            self.stdout.write(self.style.SUCCESS("No stale sessions found."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Abandoned {abandoned_count} stale session(s)."))
