"""Data migration: sync every system role's module rights to the table agreed
in the rights audit of 3 Oct 2026 (approved by the client that day).

Changes against 0015: Help Desk loses counseling.change (Report 9 #115 VIEW
ONLY); Trainer and Counsellor lose accounts.view (no document grants it; it
returned the whole CJ user list); Psychometrician gains question_bank.delete
and career_profiling.delete (Report 9 #107 — both only FILE requests for CJ
Admin); Trainer gains question_bank.delete (own drafts only); Corp Admin,
Corp Exclusive Admin and Channel Partner gain accounts.delete for their own
organization's users (Doc 9 §2.4, Report 4 CE-4/CP-4, Report 9 #5/#36/#56;
guarded in views_admin.UserViewSet.destroy).

Applies the table EXACTLY to the system roles (missing rights granted, other
rights removed); custom roles are untouched. Frozen copy of
apps.accounts.role_rights.ROLE_PERMISSIONS as of this migration.
"""

from django.db import migrations

ROLE_PERMISSIONS = {
    "cj_admin": [
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        ("accounts", "delete"),
        ("organizations", "view"),
        ("organizations", "add"),
        ("organizations", "change"),
        ("organizations", "delete"),
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("question_bank", "approve"),
        ("question_bank", "reject"),
        ("question_bank", "review"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        ("career_profiling", "view"),
        ("career_profiling", "add"),
        ("career_profiling", "change"),
        ("career_profiling", "delete"),
        ("reporting", "view"),
        ("reporting", "add"),
        ("reporting", "change"),
        ("reporting", "delete"),
        ("reporting", "generate_report"),
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("training", "delete"),
        ("counseling", "view"),
        ("counseling", "add"),
        ("counseling", "change"),
        ("counseling", "delete"),
        ("cms", "view"),
        ("cms", "add"),
        ("cms", "change"),
        ("cms", "delete"),
        ("notifications", "view"),
        ("tasks", "view"),
        ("tasks", "add"),
        ("tasks", "change"),
        ("tasks", "delete"),
        ("tasks", "assign"),
        ("tasks", "approve"),
        ("invoicing", "view"),
        ("invoicing", "add"),
        ("invoicing", "approve"),
        ("invoicing", "reject"),
        ("invoicing", "change"),
    ],
    "helpdesk": [
        ("training", "view"),
        ("counseling", "view"),
        ("notifications", "view"),
        ("accounts", "view"),
        ("organizations", "view"),
        ("assessment", "view"),
        ("career_profiling", "view"),
    ],
    "corp_admin": [
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        ("accounts", "delete"),
        ("organizations", "view"),
        ("organizations", "change"),
        ("assessment", "view"),
        ("reporting", "view"),
        ("reporting", "generate_report"),
        ("training", "view"),
        ("counseling", "view"),
    ],
    "corp_exclusive": [
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        ("accounts", "delete"),
        ("organizations", "view"),
        ("organizations", "add"),
        ("organizations", "change"),
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        ("reporting", "view"),
        ("reporting", "add"),
        ("reporting", "change"),
        ("reporting", "delete"),
        ("reporting", "generate_report"),
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("training", "delete"),
    ],
    "psychometrician": [
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("question_bank", "review"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        ("career_profiling", "view"),
        ("career_profiling", "add"),
        ("career_profiling", "change"),
        ("career_profiling", "delete"),
        ("reporting", "view"),
        ("reporting", "add"),
        ("reporting", "change"),
        ("reporting", "generate_report"),
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "sme": [
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("question_bank", "request_delete"),
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "reviewer": [
        ("question_bank", "view"),
        ("question_bank", "review"),
        ("question_bank", "approve"),
        ("question_bank", "reject"),
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "trainer": [
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("training", "delete"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "group_admin": [
        ("accounts", "view"),
        ("accounts", "add"),
        ("assessment", "view"),
        ("assessment", "assign"),
        ("organizations", "view"),
        ("organizations", "change"),
        ("reporting", "view"),
    ],
    "counsellor": [
        ("counseling", "view"),
        ("counseling", "add"),
        ("counseling", "change"),
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "channel_partner": [
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        ("accounts", "delete"),
        ("organizations", "view"),
        ("organizations", "add"),
        ("organizations", "change"),
        ("assessment", "view"),
        ("invoicing", "view"),
        ("invoicing", "add"),
    ],
    "individual": [
        ("assessment", "view"),
        ("career_profiling", "view"),
        ("reporting", "view"),
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("counseling", "view"),
        ("counseling", "add"),
        ("counseling", "change"),
    ],
}


# Frozen copy of Role.ROLE_CHOICES (a fresh database gets the system roles
# with their rights — production never runs seed_demo).
SYSTEM_ROLES = [
    ("cj_admin", "CareerJudge Admin"),
    ("helpdesk", "Help Desk"),
    ("corp_admin", "Corporate Admin"),
    ("corp_exclusive", "Corporate Exclusive"),
    ("psychometrician", "Psychometrician"),
    ("sme", "SME (Subject Matter Expert)"),
    ("reviewer", "Reviewer"),
    ("trainer", "Trainer"),
    ("group_admin", "Group Admin"),
    ("counsellor", "Counsellor"),
    ("channel_partner", "Channel Partner"),
    ("individual", "Individual"),
]


def sync(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    ModuleRight = apps.get_model("accounts", "ModuleRight")
    for name, label in SYSTEM_ROLES:
        Role.objects.get_or_create(
            name=name, defaults={"description": label, "is_system": True, "is_frozen": True}
        )
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
        ("accounts", "0016_userprofile_domains_of_expertise"),
    ]
    operations = [
        migrations.RunPython(sync, reverse_code=migrations.RunPython.noop),
    ]
