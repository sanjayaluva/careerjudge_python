"""Seed demo data: 1 user per role + sample permissions + 1 superuser.

Usage:
    python manage.py seed_demo

Creates:
- 11 system roles (cj_admin, corp_admin, corp_exclusive, psychometrician,
  sme, reviewer, trainer, group_admin, counsellor, channel_partner, individual)
- 11 demo users (one per role) with predictable passwords
- 1 superuser for emergency access
- Sample module rights per role (view/add/change/delete on relevant modules)

SME vs Reviewer (split per client clarification 2026-06-30):
  - sme:      creates/views/edits/deletes OWN questions (unreviewed only).
              Once reviewed, can only `request_delete` (admin approves).
  - reviewer: reviews questions, approves/rejects. No create/edit/delete.

Idempotent - safe to run multiple times.
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
    ("sme", "sme@demo.careerjudge.pp.ua", "SME User", "Demo@1234"),
    ("reviewer", "reviewer@demo.careerjudge.pp.ua", "Reviewer", "Demo@1234"),
    ("trainer", "trainer@demo.careerjudge.pp.ua", "Trainer", "Demo@1234"),
    ("group_admin", "group.admin@demo.careerjudge.pp.ua", "Group Admin", "Demo@1234"),
    ("counsellor", "counsellor@demo.careerjudge.pp.ua", "Counsellor", "Demo@1234"),
    ("channel_partner", "channel.partner@demo.careerjudge.pp.ua", "Channel Partner", "Demo@1234"),
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
        ("question_bank", "approve"),
        ("question_bank", "reject"),
        ("question_bank", "review"),
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
        # Psychometrician: full QB access (configures psychometric properties)
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "review"),
        # Psychometrician is the primary assessment author per SRS UC029
        # "Prepare Assessment Blueprint" — full CRUD on assessments.
        ("assessment", "view"),
        ("assessment", "add"),
        ("assessment", "change"),
        ("assessment", "delete"),
        ("career_profiling", "view"),
        ("career_profiling", "change"),
        ("reporting", "view"),
    ],
    "sme": [
        # SME: creates/edits/deletes OWN questions (unreviewed only).
        # Once reviewed, can only request_delete (admin approves).
        ("question_bank", "view"),
        ("question_bank", "add"),
        ("question_bank", "change"),
        ("question_bank", "delete"),
        ("question_bank", "request_delete"),
        ("assessment", "view"),
    ],
    "reviewer": [
        # Reviewer: reviews questions, approves/rejects. No create/edit/delete.
        ("question_bank", "view"),
        ("question_bank", "review"),
        ("question_bank", "approve"),
        ("question_bank", "reject"),
        ("assessment", "view"),
    ],
    "trainer": [
        ("training", "view"),
        ("training", "add"),
        ("training", "change"),
        ("training", "delete"),
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
    "channel_partner": [
        # Channel Partner: manages their own individual users + assessments
        ("accounts", "view"),
        ("accounts", "add"),
        ("accounts", "change"),
        ("organizations", "view"),
        ("organizations", "change"),
        ("assessment", "view"),
        ("assessment", "add"),
        ("reporting", "view"),
        ("reporting", "generate_report"),
    ],
    "individual": [
        ("assessment", "view"),  # can take assessments
        ("reporting", "view"),  # can view own reports
        ("training", "view"),  # can browse + register for courses
        ("training", "add"),  # can register (register action = 'add')
        ("training", "change"),  # can track progress (progress action = 'change')
        ("counseling", "view"),  # can browse counsellors
        ("counseling", "add"),  # can book sessions
        ("counseling", "change"),  # can submit feedback
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
            # ALWAYS reset the password for demo users — these are documented
            # credentials (README + seed_demo output) and must always work
            # after running this command. Without this, existing users keep
            # whatever password they had, causing "Invalid credentials" errors.
            user.set_password(password)
            # Ensure role + profile fields are current
            user.full_name = full_name
            user.is_active = True
            user.is_email_verified = True
            user.role = roles[role_name]
            user.save()
            UserProfile.objects.get_or_create(user=user)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Created: {email} / {password} (role: {role_name})")
                )
            else:
                self.stdout.write(f"  → Exists (password reset): {email}")

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
        # Always reset the superuser password too (same rationale as demo users).
        superuser.set_password("Su@12345678")
        superuser.is_superuser = True
        superuser.is_staff = True
        superuser.is_active = True
        superuser.is_email_verified = True
        superuser.save()
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    "  ✓ Created superuser: superuser@careerjudge.pp.ua / Su@12345678"
                )
            )
        else:
            self.stdout.write("  → Superuser exists (password reset).")

        self.stdout.write(self.style.SUCCESS("\n✓ Demo seed complete."))
        self.stdout.write("\nDemo login credentials:")
        for role_name, email, _, password in DEMO_USERS:
            self.stdout.write(f"  {role_name:<18} → {email} / {password}")
