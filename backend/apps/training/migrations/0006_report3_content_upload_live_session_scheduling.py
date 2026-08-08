"""Report 3 §OS.1/§OL.1/§7.4 — content document upload + live-session scheduling.

Per System Testing & Review Feedback Report 3 (30-07-2026):
  - SessionContent gains a `document` FileField (PDF/Word/PPT) + a new
    'document' content format (§OS.1: upload PDF/Word/PPT directly).
  - LiveSession gains schedule_mode (advance/ongoing) + depends_on (§OL.1)
    + rescheduled_from / reschedule_reason (§7.4/§OL.2 reschedule audit).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0005_report3_course_update_request_live_session_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessioncontent",
            name="document",
            field=models.FileField(
                blank=True,
                help_text="Uploaded PDF/Word/PPT document (document format).",
                null=True,
                upload_to="session_documents/",
                verbose_name="document",
            ),
        ),
        migrations.AlterField(
            model_name="sessioncontent",
            name="content_format",
            field=models.CharField(
                choices=[
                    ("video", "Video"),
                    ("audio", "Audio"),
                    ("text", "Text"),
                    ("document", "Document (PDF / Word / PPT)"),
                ],
                default="video",
                max_length=10,
                verbose_name="content format",
            ),
        ),
        migrations.AddField(
            model_name="livesession",
            name="schedule_mode",
            field=models.CharField(
                choices=[
                    ("advance", "Advance (fixed date set ahead of time)"),
                    ("ongoing", "Ongoing (trainer schedules based on the preceding session)"),
                ],
                default="advance",
                max_length=10,
                verbose_name="schedule mode",
            ),
        ),
        migrations.AddField(
            model_name="livesession",
            name="depends_on",
            field=models.ForeignKey(
                blank=True,
                help_text="Ongoing mode: the preceding session this one waits on.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="dependent_sessions",
                to="training.livesession",
            ),
        ),
        migrations.AddField(
            model_name="livesession",
            name="rescheduled_from",
            field=models.DateTimeField(blank=True, null=True, verbose_name="rescheduled from"),
        ),
        migrations.AddField(
            model_name="livesession",
            name="reschedule_reason",
            field=models.TextField(blank=True, default="", verbose_name="reschedule reason"),
        ),
    ]
