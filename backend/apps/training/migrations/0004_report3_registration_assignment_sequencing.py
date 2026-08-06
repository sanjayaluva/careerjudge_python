"""Report 3 (Training) — registration form, assignment improvements, sequencing.

Adds fields per System Testing & Review Feedback Report 3 (30-07-2026):
  - CourseRegistration.registration_form: JSON snapshot of the registration
    form (profile-prefilled answers) at registration time. (§1.1)
  - Assignment.is_report_mandatory + submission_deadline. (§3.3, §3.4)
  - AssignmentReport.report_file (real FileField upload) +
    late_submission_approved flag. (§3.3, §3.6)
  - TrainingCourse.enforce_sequence: sequential vs free content navigation. (§5.1)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0003_consent_interactive"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseregistration",
            name="registration_form",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Snapshot of registration-form answers (prefilled from profile + "
                    "any extra answers the candidate provided) at registration time."
                ),
                verbose_name="registration form",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="is_report_mandatory",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If True, the candidate cannot advance past this assignment's "
                    "session until the report is submitted and reviewed (SRS §2.3.2)."
                ),
                verbose_name="report submission mandatory",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="submission_deadline",
            field=models.DateTimeField(
                blank=True,
                help_text="After this datetime, submission requires trainer approval.",
                null=True,
                verbose_name="submission deadline",
            ),
        ),
        migrations.AddField(
            model_name="assignmentreport",
            name="late_submission_approved",
            field=models.BooleanField(
                default=False,
                help_text=("Set by the trainer to allow submission after the deadline has passed."),
                verbose_name="late submission approved",
            ),
        ),
        migrations.AddField(
            model_name="assignmentreport",
            name="report_file",
            field=models.FileField(
                blank=True,
                help_text="Uploaded report file (PDF, PPT, Word, etc.).",
                null=True,
                upload_to="assignment_reports/",
                verbose_name="report file upload",
            ),
        ),
        migrations.AddField(
            model_name="trainingcourse",
            name="enforce_sequence",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If True, candidates must complete contents in sequential order "
                    "and cannot skip ahead (SRS §2.4.1.2). If False, free navigation."
                ),
                verbose_name="enforce content sequence",
            ),
        ),
    ]
