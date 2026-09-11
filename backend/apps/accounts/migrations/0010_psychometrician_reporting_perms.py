"""Data migration: grant `reporting.generate_report` to the psychometrician role.

The psychometrician role only had `reporting.view` — they could see reports
but not generate them. Per SRS, psychometricians configure assessments and
review results, so they also need to generate the reports that come out of
that work.

This migration is idempotent — safe to run multiple times. It only adds the
permission if it doesn't already exist on the role. seed_demo.py is updated
in parallel so fresh installs also receive this permission.
"""
from django.db import migrations

PERMS_TO_GRANT = [
    ("reporting", "generate_report"),
]


def grant_perms(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    ModuleRight = apps.get_model("accounts", "ModuleRight")
    try:
        role = Role.objects.get(name="psychometrician")
    except Role.DoesNotExist:
        # Role not yet created — seed_demo will create it with the correct
        # permissions next time it runs.
        return
    for module, action in PERMS_TO_GRANT:
        ModuleRight.objects.get_or_create(role=role, module=module, action=action)


def revoke_perms(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    ModuleRight = apps.get_model("accounts", "ModuleRight")
    try:
        role = Role.objects.get(name="psychometrician")
    except Role.DoesNotExist:
        return
    for module, action in PERMS_TO_GRANT:
        ModuleRight.objects.filter(role=role, module=module, action=action).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_trainer_assessment_qb_perms"),
    ]
    operations = [
        migrations.RunPython(grant_perms, reverse_code=revoke_perms),
    ]
