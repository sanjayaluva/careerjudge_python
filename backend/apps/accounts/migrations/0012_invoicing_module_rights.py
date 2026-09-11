"""Data migration: grant `invoicing` module rights (H14).

Per Doc 4, the empanelled roles (SME, Reviewer, Trainer, Counsellor, Channel
Partner, Psychometrician) can create/submit invoices to CJ Admin, who
reviews/approves/rejects/pays them. This grants the matching ModuleRight rows
so the Invoicing nav entry + create action are gated the same way every
other module already is.

Idempotent — safe to run multiple times. seed_demo.py is updated in
parallel so fresh installs also receive these permissions.
"""
from django.db import migrations

EMPANELLED_PERMS = [
    ("invoicing", "view"),
    ("invoicing", "add"),
]

ADMIN_PERMS = [
    ("invoicing", "view"),
    ("invoicing", "add"),
    ("invoicing", "approve"),
    ("invoicing", "reject"),
    ("invoicing", "change"),
]

ROLE_PERMS = {
    "cj_admin": ADMIN_PERMS,
    "psychometrician": EMPANELLED_PERMS,
    "sme": EMPANELLED_PERMS,
    "reviewer": EMPANELLED_PERMS,
    "trainer": EMPANELLED_PERMS,
    "counsellor": EMPANELLED_PERMS,
    "channel_partner": EMPANELLED_PERMS,
}


def grant_perms(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    ModuleRight = apps.get_model("accounts", "ModuleRight")
    for role_name, perms in ROLE_PERMS.items():
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            # Role not yet created — seed_demo will create it with the
            # correct permissions next time it runs.
            continue
        for module, action in perms:
            ModuleRight.objects.get_or_create(role=role, module=module, action=action)


def revoke_perms(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    ModuleRight = apps.get_model("accounts", "ModuleRight")
    for role_name, perms in ROLE_PERMS.items():
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            continue
        for module, action in perms:
            ModuleRight.objects.filter(role=role, module=module, action=action).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_alter_moduleright_module"),
    ]
    operations = [
        migrations.RunPython(grant_perms, reverse_code=revoke_perms),
    ]
