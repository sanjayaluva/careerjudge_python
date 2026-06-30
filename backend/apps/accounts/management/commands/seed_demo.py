"""Seed demo data: 1 user per role + sample permissions + 1 superuser.

Usage:
    python manage.py seed_demo

Creates:
- 9 roles (cj_admin, corp_admin, corp_exclusive, psychometrician,
  sme_reviewer, trainer, group_admin, counsellor, individual)
- 9 demo users (one per role) with predictable passwords
- 1 superuser for emergency access
- Sample module rights per role (view/add/change/delete on relevant modules)

Idempotent — safe to run multiple times.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import UserProfile
from apps.accounts.services import (
    assign_permission_to_role,
    get_or_create_default_roles,
)

User = get_user_model()


DEMO_USERS = [
    # (role_name, email, full_name, password)
    ("cj_admin", "cj.admin@demo.careerjudge.pp.ua", "CJ Admin", "Demo@1234"),
    ("corp_admin", "corp.admin@demo.careerjudge.pp.ua", "Corp Admin", "Demo@1234"),
    ("corp_exclusive", "corp.exclusive@demo.careerjudge.pp.ua", "Corp Exclusive", "Demo@1234"),
    ("psychometrician", "psychometrician@demo.careerjudge.pp.ua", "Psychometrician", "Demo@1234"),
    ("sme_reviewer", "sme.reviewer@demo.careerjudge.pp.ua", "SME Reviewer", "Demo@1234"),
    ("trainer", "trainer@demo.careerjudge.pp.ua", "Trainer", "Demo@1234"),
    ("group_admin", "group.admin@demo.careerjudge.pp.ua", "Group Admin", "Demo@1234"),
    ("counsellor", "counsellor@demo.careerjudge.pp.ua", "Counsellor", "Demo@1234"),
    ("individual", "individual@demo.careerjudge.pp.ua", "Individual User", "Demo@1234"),
]


# Role → list of (module, action) rights
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
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        ("career_profiling", "view"),
        ("career_profiling", "change"),
        ("reporting", "view"),
        ("reporting", "generate_report"),
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("counseling", "view"),
        ("counseling", "add"),
        ("counseling", "change"),
        ("cms", "view"),
        ("cms", "add"),
        ("cms", "change"),
        ("cms", "delete"),
        ("notifications", "view"),
    ],
    "corp_admin": [
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        ("organizations", "view"),
        ("organizations", "change"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("reporting", "view"),
        ("reporting", "generate_report"),
        ("training", "view"),
        ("training", "add"),
        ("counseling", "view"),
    ],
    "corp_exclusive": [
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        ("organizations", "view"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("reporting", "view"),
        ("reporting", "generate_report"),
    ],
    "psychometrician": [
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("assessment", "view"),
        ("reporting", "view"),
    ],
    "sme_reviewer": [
        ("question_bank", "view"),
        ("question_bank", "approve"),
        ("assessment", "view"),
    ],
    "trainer": [
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("accounts", "view"),
        ("assessment", "view"),
    ],
    "group_admin": [
        ("accounts", "view"),
        ("assessment", "view"),
        ("assessment", "assign"),
        ("organizations", "view"),
    ],
    "counsellor": [
        ("counseling", "view"),
        ("counseling", "add"),
        ("counseling", "change"),
        ("accounts", "view"),
        ("assessment", "view"),
        ("reporting", "view"),
    ],
    "individual": [
        ("assessment", "view"),  # can take assessments
        ("reporting", "view"),  # can view own reports
    ],
}


class Command(BaseCommand):
    help = "Seed demo roles, users, and permissions."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("→ Creating default roles…"))
        roles = get_or_create_default_roles()
        for name, _role in roles.items():
            self.stdout.write(f"  ✓ Role: {name}")

        self.stdout.write(self.style.MIGRATE_HEADING("→ Assigning permissions to roles…"))
        for role_name, perms in ROLE_PERMISSIONS.items():
            role = roles[role_name]
            for module, action in perms:
                assign_permission_to_role(role, module, action)
            self.stdout.write(f"  ✓ {role_name}: {len(perms)} permissions")

        self.stdout.write(self.style.MIGRATE_HEADING("→ Creating demo users (1 per role)…"))
        for role_name, email, full_name, password in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "is_active": True,
                    "is_email_verified": True,
                    "role": roles[role_name],
                },
            )
            if created:
                user.set_password(password)
                user.save()
                UserProfile.objects.get_or_create(user=user)
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Created: {email} / {password} (role: {role_name})")
                )
            else:
                # Ensure role is set
                if user.role_id != roles[role_name].id:
                    user.role = roles[role_name]
                    user.save(update_fields=["role", "updated_at"])
                self.stdout.write(f"  → Exists: {email}")

        self.stdout.write(self.style.MIGRATE_HEADING("→ Creating superuser…"))
        superuser, created = User.objects.get_or_create(
            email="superuser@careerjudge.pp.ua",
            defaults={
                "is_superuser": True,
                "is_staff": True,
                "is_active": True,
                "is_email_verified": True,
                "full_name": "Superuser",
            },
        )
        if created:
            superuser.set_password("Su@12345678")
            superuser.save()
            self.stdout.write(
                self.style.SUCCESS(
                    "  ✓ Created superuser: superuser@careerjudge.pp.ua / Su@12345678"
                )
            )
        else:
            self.stdout.write("  → Superuser exists.")

        self.stdout.write(self.style.SUCCESS("\n✓ Demo seed complete."))
        self.stdout.write("\nDemo login credentials:")
        for role_name, email, _, password in DEMO_USERS:
            self.stdout.write(f"  {role_name:<18} → {email} / {password}")
