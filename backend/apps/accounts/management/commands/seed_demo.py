"""Seed demo data: 1 user per role + sample permissions + 1 superuser.

Usage:
    python manage.py seed_demo

Creates:
- 11 system roles (cj_admin, corp_admin, corp_exclusive, psychometrician,
  sme, reviewer, trainer, group_admin, counsellor, channel_partner, individual)
- 11 demo users (one per role) with predictable passwords
- 1 superuser for emergency access
- Module rights per role, synced exactly to apps.accounts.role_rights

SME vs Reviewer (split per client clarification 2026-06-30):
  - sme:      creates/views/edits/deletes OWN questions (unreviewed only).
              Once reviewed, can only `request_delete` (admin approves).
  - reviewer: reviews questions, approves/rejects. No create/edit/delete.

Idempotent - safe to run multiple times.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import ModuleRight, Role, UserProfile
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles

User = get_user_model()


DEMO_USERS = [
    # (role_name, email, full_name, password)
    ("cj_admin", "cj.admin@demo.careerjudge.pp.ua", "CJ Admin", "Demo@1234"),
    ("helpdesk", "helpdesk@demo.careerjudge.pp.ua", "Help Desk", "Demo@1234"),
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
    # Report 3: helpdesk receives counselling booking/slot/followup notifications
]


# Role rights live in apps.accounts.role_rights (single source of truth).


class Command(BaseCommand):
    help = "Seed demo roles, users, and permissions."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("→ Creating default roles…"))
        roles = get_or_create_default_roles()
        for name, _role in roles.items():
            self.stdout.write(f"  ✓ Role: {name}")

        self.stdout.write(self.style.MIGRATE_HEADING("→ Assigning permissions to roles…"))
        # Exact sync: grants missing rights AND removes rights a system role
        # should no longer have (earlier seeds only ever added).
        changes = sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
        for role_name, perms in ROLE_PERMISSIONS.items():
            added, removed = changes.get(role_name, (0, 0))
            self.stdout.write(f"  ✓ {role_name}: {len(perms)} permissions (+{added} / -{removed})")

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

        # Create a CounsellorProfile for the demo counsellor user
        self.stdout.write(self.style.MIGRATE_HEADING("→ Creating counsellor profile…"))
        from apps.counseling.models import CounsellorProfile

        counsellor_user = User.objects.filter(email="counsellor@demo.careerjudge.pp.ua").first()
        if counsellor_user:
            # Set counsellor-specific fields on UserProfile
            up, _ = UserProfile.objects.get_or_create(user=counsellor_user)
            up.bio = "Experienced career counsellor with expertise in aptitude assessment and career guidance."
            up.hourly_rate = 50
            up.is_available_for_counseling = True
            up.save()

            # Create the CounsellorProfile (links user + categories M2M)
            cp, created = CounsellorProfile.objects.get_or_create(user=counsellor_user)
            if created:
                self.stdout.write(self.style.SUCCESS("  ✓ Created counsellor profile"))
            else:
                self.stdout.write("  → Counsellor profile exists")

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
