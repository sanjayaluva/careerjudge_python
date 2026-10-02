"""Data migration: sync every system role's module rights to the corrected
table (Report 9, 1 Oct 2026).

Earlier rights changes were made only in seed_demo, which only ever ADDED
rights, so removals (e.g. Report 4: no Assessments for Counsellor, SME and
Reviewer) never reached existing databases, and production never ran the seed
at all. This migration applies the table below EXACTLY to the system roles:
missing rights are granted and any other right is removed. Custom roles are
untouched.

The table is a frozen copy of apps.accounts.role_rights.ROLE_PERMISSIONS as of
this migration.
"""

from django.db import migrations

ROLE_PERMISSIONS = {'cj_admin': [('accounts', 'view'),
              ('accounts', 'add'),
              ('accounts', 'change'),
              ('accounts', 'delete'),
              ('organizations', 'view'),
              ('organizations', 'add'),
              ('organizations', 'change'),
              ('organizations', 'delete'),
              ('question_bank', 'view'),
              ('question_bank', 'add'),
              ('question_bank', 'change'),
              ('question_bank', 'delete'),
              ('question_bank', 'approve'),
              ('question_bank', 'reject'),
              ('question_bank', 'review'),
              ('assessment', 'view'),
              ('assessment', 'add'),
              ('assessment', 'change'),
              ('assessment', 'delete'),
              ('career_profiling', 'view'),
              ('career_profiling', 'add'),
              ('career_profiling', 'change'),
              ('career_profiling', 'delete'),
              ('reporting', 'view'),
              ('reporting', 'add'),
              ('reporting', 'change'),
              ('reporting', 'delete'),
              ('reporting', 'generate_report'),
              ('training', 'view'),
              ('training', 'add'),
              ('training', 'change'),
              ('training', 'delete'),
              ('counseling', 'view'),
              ('counseling', 'add'),
              ('counseling', 'change'),
              ('counseling', 'delete'),
              ('cms', 'view'),
              ('cms', 'add'),
              ('cms', 'change'),
              ('cms', 'delete'),
              ('notifications', 'view'),
              ('tasks', 'view'),
              ('tasks', 'add'),
              ('tasks', 'change'),
              ('tasks', 'delete'),
              ('tasks', 'assign'),
              ('tasks', 'approve'),
              ('invoicing', 'view'),
              ('invoicing', 'add'),
              ('invoicing', 'approve'),
              ('invoicing', 'reject'),
              ('invoicing', 'change')],
 'helpdesk': [('training', 'view'),
              ('counseling', 'view'),
              ('counseling', 'change'),
              ('notifications', 'view'),
              ('accounts', 'view')],
 'corp_admin': [('accounts', 'view'),
                ('accounts', 'add'),
                ('accounts', 'change'),
                ('organizations', 'view'),
                ('organizations', 'change'),
                ('assessment', 'view'),
                ('reporting', 'view'),
                ('reporting', 'generate_report'),
                ('training', 'view'),
                ('counseling', 'view')],
 'corp_exclusive': [('accounts', 'view'),
                    ('accounts', 'add'),
                    ('accounts', 'change'),
                    ('organizations', 'view'),
                    ('organizations', 'change'),
                    ('assessment', 'view'),
                    ('reporting', 'view'),
                    ('reporting', 'generate_report')],
 'psychometrician': [('question_bank', 'view'),
                     ('question_bank', 'add'),
                     ('question_bank', 'change'),
                     ('question_bank', 'review'),
                     ('assessment', 'view'),
                     ('assessment', 'add'),
                     ('assessment', 'change'),
                     ('assessment', 'delete'),
                     ('career_profiling', 'view'),
                     ('career_profiling', 'add'),
                     ('career_profiling', 'change'),
                     ('reporting', 'view'),
                     ('reporting', 'add'),
                     ('reporting', 'change'),
                     ('reporting', 'generate_report'),
                     ('invoicing', 'view'),
                     ('invoicing', 'add')],
 'sme': [('question_bank', 'view'),
         ('question_bank', 'add'),
         ('question_bank', 'change'),
         ('question_bank', 'delete'),
         ('question_bank', 'request_delete'),
         ('invoicing', 'view'),
         ('invoicing', 'add')],
 'reviewer': [('question_bank', 'view'),
              ('question_bank', 'review'),
              ('question_bank', 'approve'),
              ('question_bank', 'reject'),
              ('invoicing', 'view'),
              ('invoicing', 'add')],
 'trainer': [('training', 'view'),
             ('training', 'add'),
             ('training', 'change'),
             ('training', 'delete'),
             ('accounts', 'view'),
             ('assessment', 'view'),
             ('assessment', 'add'),
             ('assessment', 'change'),
             ('assessment', 'delete'),
             ('question_bank', 'view'),
             ('question_bank', 'add'),
             ('question_bank', 'change'),
             ('invoicing', 'view'),
             ('invoicing', 'add')],
 'group_admin': [('accounts', 'view'),
                 ('assessment', 'view'),
                 ('assessment', 'assign'),
                 ('organizations', 'view'),
                 ('organizations', 'change')],
 'counsellor': [('counseling', 'view'),
                ('counseling', 'add'),
                ('counseling', 'change'),
                ('accounts', 'view'),
                ('invoicing', 'view'),
                ('invoicing', 'add')],
 'channel_partner': [('accounts', 'view'),
                     ('accounts', 'add'),
                     ('accounts', 'change'),
                     ('organizations', 'view'),
                     ('organizations', 'change'),
                     ('assessment', 'view'),
                     ('invoicing', 'view'),
                     ('invoicing', 'add')],
 'individual': [('assessment', 'view'),
                ('reporting', 'view'),
                ('training', 'view'),
                ('training', 'add'),
                ('training', 'change'),
                ('counseling', 'view'),
                ('counseling', 'add'),
                ('counseling', 'change')]}


def sync(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    ModuleRight = apps.get_model("accounts", "ModuleRight")
    for role_name, perms in ROLE_PERMISSIONS.items():
        role = Role.objects.filter(name=role_name).first()
        if role is None:
            continue
        wanted = set(perms)
        current = {(r.module, r.action): r.pk for r in ModuleRight.objects.filter(role=role)}
        for module, action in wanted - current.keys():
            ModuleRight.objects.create(role=role, module=module, action=action)
        stale = [current[key] for key in current.keys() - wanted]
        if stale:
            ModuleRight.objects.filter(pk__in=stale).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0014_counsellor_languages_age"),
    ]
    operations = [
        migrations.RunPython(sync, reverse_code=migrations.RunPython.noop),
    ]
