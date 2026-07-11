"""Data migration: grant assessment CRUD permissions to the psychometrician role.

Per SRS UC029 "Prepare Assessment Blueprint", the psychometrician is the
primary author of assessments. The original seed_demo only granted
`assessment.view` to psychometrician, which blocked them from creating
or managing assessments — even though the frontend already shows them
the Create/Edit/Delete buttons.

This migration is idempotent — safe to run multiple times. It only adds
permissions that don't already exist on the role.
"""
from django.db import migrations


PERMS_TO_GRANT = [
    ("assessment", "add"),
    ("assessment", "change"),
    ("assessment", "delete"),
    # career_profiling change was also missing from the original seed
    ("career_profiling", "change"),
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
        ("accounts", "0005_remove_userprofile_country_remove_userprofile_state_and_more"),
        ("assessment", "0002_assessment_assessment_type"),
    ]
    operations = [
        migrations.RunPython(grant_perms, reverse_code=revoke_perms),
    ]
