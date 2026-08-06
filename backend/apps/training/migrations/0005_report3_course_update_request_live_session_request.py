"""Report 3 §6/§7 — course-update approval workflow + live-session requests.

Adds two models per System Testing & Review Feedback Report 3 (30-07-2026):
  - CourseUpdateRequest: trainer requests admin approval to update or delete a
    PUBLISHED course (§7.1, §7.2).
  - LiveSessionRequest: candidate asks the trainer to schedule an unscheduled
    live session (§7.5, OS.4).
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("training", "0004_report3_registration_assignment_sequencing"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseUpdateRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "request_type",
                    models.CharField(
                        choices=[("update", "Update published course"), ("delete", "Delete published course")],
                        max_length=10,
                        verbose_name="request type",
                    ),
                ),
                ("reason", models.TextField(help_text="Why the change is needed.", verbose_name="reason")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending admin review"),
                            ("approved", "Approved by admin"),
                            ("declined", "Declined by admin"),
                        ],
                        default="pending",
                        max_length=10,
                        verbose_name="status",
                    ),
                ),
                (
                    "admin_note",
                    models.TextField(
                        blank=True, default="", help_text="Admin's response note.", verbose_name="admin note"
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="reviewed at")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="update_requests",
                        to="training.trainingcourse",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="training_course_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_course_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "course update request",
                "verbose_name_plural": "course update requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LiveSessionRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "preferred_times",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of candidate-preferred date/times (ISO strings).",
                        verbose_name="preferred times",
                    ),
                ),
                ("note", models.TextField(blank=True, default="", verbose_name="note")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending — trainer has not scheduled yet"),
                            ("scheduled", "Trainer scheduled a session"),
                            ("declined", "Trainer declined"),
                        ],
                        default="pending",
                        max_length=10,
                        verbose_name="status",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="live_session_requests",
                        to="training.trainingcourse",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="live_session_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "scheduled_session",
                    models.ForeignKey(
                        blank=True,
                        help_text="The LiveSession created in response to this request.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="originating_requests",
                        to="training.livesession",
                    ),
                ),
            ],
            options={
                "verbose_name": "live session request",
                "verbose_name_plural": "live session requests",
                "ordering": ["-created_at"],
            },
        ),
    ]
