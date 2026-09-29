"""Re-run scoring for completed assessment sessions.

Scoring fixes (e.g. Report 7: 2b/2c/2d partial credit, negative marking)
apply to new submissions automatically; stored results of sessions already
completed keep their old scores until re-scored with this command.

    python manage.py rescore_sessions --dry-run            # show what changes
    python manage.py rescore_sessions --assessment 12      # one assessment
    python manage.py rescore_sessions                      # every completed session

Re-scoring is idempotent (scores are recomputed and upserted).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import AssessmentSession
from apps.assessment.scoring import calculate_session_scores


class Command(BaseCommand):
    help = "Recalculate scores for completed assessment sessions."

    def add_arguments(self, parser):
        parser.add_argument("--assessment", type=int, help="Only this assessment id.")
        parser.add_argument("--dry-run", action="store_true", help="Report changes without saving.")

    def handle(self, *args, assessment=None, dry_run=False, **options):
        sessions = AssessmentSession.objects.filter(status="completed").order_by("id")
        if assessment:
            sessions = sessions.filter(assessment_id=assessment)

        changed = 0
        for session in sessions:
            before = (session.total_score, session.max_score)
            with transaction.atomic():
                sid = transaction.savepoint()
                calculate_session_scores(session)
                session.refresh_from_db(fields=["total_score", "max_score"])
                after = (session.total_score, session.max_score)
                if dry_run:
                    transaction.savepoint_rollback(sid)
            if before != after:
                changed += 1
                self.stdout.write(
                    f"session {session.id} ({session.assessment_id}): "
                    f"{before[0]}/{before[1]} -> {after[0]}/{after[1]}"
                )
        verb = "would change" if dry_run else "changed"
        self.stdout.write(
            self.style.SUCCESS(f"{sessions.count()} sessions checked, {changed} {verb}.")
        )
