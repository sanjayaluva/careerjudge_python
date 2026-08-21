"""Report 3 §4.1: grant trainers assessment authoring + question-bank access.

Per the System Testing & Review Feedback Report 3 (30-07-2026) §4.1: trainers
should be able to CREATE assessments using the CJ Question Bank (selecting and
assigning questions), without access to the entire pool of assessments. This
migration grants the trainer role:

  - assessment: add, change, delete (so they can author + manage their own
    course assessments; the assessment viewset scopes their list to their own
    via created_by — see assessment/views.py get_queryset).
  - question_bank: view, add, change (so they can browse their own questions
    and create new ones; the QB viewset scopes their list to created_by).

Idempotent: safe to run multiple times. seed_demo.py is updated in parallel so
fresh installs also receive these permissions.
"""

from django.db import migrations

TRAINING_PERMS = [
    # (module, action)
    ("assessment", "add"),
    ("assessment", "change"),
    ("assessment", "delete"),
    ("question_bank", "view"),
    ("question_bank", "add"),
    ("question_bank", "change"),
]


def grant_trainer_perms(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    ModuleRight = apps.get_model("accounts", "ModuleRight")
    try:
        trainer = Role.objects.get(name="trainer")
    except Role.DoesNotExist:
        return
    for module, action in TRAINING_PERMS:
        ModuleRight.objects.get_or_create(role=trainer, module=module, action=action)


def revoke_trainer_perms(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    ModuleRight = apps.get_model("accounts", "ModuleRight")
    try:
        trainer = Role.objects.get(name="trainer")
    except Role.DoesNotExist:
        return
    for module, action in TRAINING_PERMS:
        ModuleRight.objects.filter(role=trainer, module=module, action=action).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_userprofile_geographical_location_and_more"),
    ]

    operations = [
        migrations.RunPython(grant_trainer_perms, reverse_code=revoke_trainer_perms),
    ]
