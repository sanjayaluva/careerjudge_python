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
    # Report 9: a corporate employee, so organization-limited behaviour can be
    # tested (the plain "individual" stays a non-corporate user).
    ("individual", "employee@demo.careerjudge.pp.ua", "Demo Employee", "Demo@1234"),
    # Report 3: helpdesk receives counselling booking/slot/followup notifications
]

# Report 9: the demo organization managers belonged to no organization, so
# nothing organization-limited could be shown. Each is tagged to a demo
# organization of the right type (created once; client data is untouched).
# (organization name, type, [(user email, is_admin, group name or None)])
DEMO_ORGANIZATIONS = [
    (
        "Demo Corporate Ltd",
        "corporate",
        [
            ("corp.admin@demo.careerjudge.pp.ua", True, None),
            ("group.admin@demo.careerjudge.pp.ua", True, "Demo Group A"),
            ("employee@demo.careerjudge.pp.ua", False, "Demo Group A"),
        ],
    ),
    (
        "Demo Exclusive Ltd",
        "corp_exclusive",
        [("corp.exclusive@demo.careerjudge.pp.ua", True, None)],
    ),
    (
        "Demo Channel Partner Agency",
        "channel_partner",
        [("channel.partner@demo.careerjudge.pp.ua", True, None)],
    ),
]

SAMPLE_REPORT_TITLE = "Sample Descriptive Report"
SAMPLE_SOLUTION_TITLE = "Sample Career Profiling Solution"


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

        self._seed_demo_organizations()
        self._seed_sample_reporting_content()

        self.stdout.write(self.style.SUCCESS("\n✓ Demo seed complete."))
        self.stdout.write("\nDemo login credentials:")
        for role_name, email, _, password in DEMO_USERS:
            self.stdout.write(f"  {role_name:<18} → {email} / {password}")

    def _seed_demo_organizations(self):
        """Tag each demo organization manager to a demo organization (Report 9)
        and give the demo organizations the first published assessment, so
        schedules and members' views can be tried. Never touches client data."""
        from apps.assessment.models import Assessment
        from apps.organizations.models import (
            Group,
            Organization,
            OrganizationAssignment,
            OrganizationMember,
        )

        self.stdout.write(self.style.MIGRATE_HEADING("→ Demo organizations…"))
        first_published = Assessment.objects.filter(status="published").order_by("id").first()
        for name, org_type, members in DEMO_ORGANIZATIONS:
            org, created = Organization.objects.get_or_create(
                name=name, defaults={"type": org_type, "status": "active"}
            )
            for email, is_admin, group_name in members:
                user = User.objects.filter(email=email).first()
                if user is None:
                    continue
                group = None
                if group_name:
                    group, _ = Group.objects.get_or_create(organization=org, name=group_name)
                OrganizationMember.objects.update_or_create(
                    organization=org,
                    user=user,
                    defaults={"is_admin": is_admin, "group": group},
                )
            if first_published is not None:
                OrganizationAssignment.objects.get_or_create(
                    organization=org, item_type="assessment", item_id=first_published.id
                )
            self.stdout.write(f"  {'✓ Created' if created else '→ Exists'}: {name}")

    def _seed_sample_reporting_content(self):
        """Report 9 #118/#119: give Reports and Profiling something to review —
        a published sample report (with reports generated for the demo users'
        completed attempts) and a draft sample profiling solution. Created once
        and only when a published assessment exists."""
        from apps.assessment.models import Assessment, AssessmentSession
        from apps.career_profiling.models import ProfilingSolution, SelectedAssessment
        from apps.reporting.generation import generate_report_data
        from apps.reporting.models import GeneratedReport, Report

        self.stdout.write(self.style.MIGRATE_HEADING("→ Sample report and profiling content…"))
        demo_emails = [email for _, email, _, _ in DEMO_USERS]
        completed = AssessmentSession.objects.filter(
            status="completed", assessment__status="published"
        )
        preferred = completed.filter(candidate__email__in=demo_emails).order_by("-id").first()
        assessment = (
            preferred.assessment
            if preferred
            else Assessment.objects.filter(status="published").order_by("id").first()
        )
        if assessment is None:
            self.stdout.write("  → No published assessment yet; skipped.")
            return
        admin = User.objects.filter(email="cj.admin@demo.careerjudge.pp.ua").first()

        report, created = Report.objects.get_or_create(
            title=SAMPLE_REPORT_TITLE,
            defaults={
                "objective": "A ready-made example to explore report set-up and generation.",
                "report_type": "descriptive",
                "scope": "general",
                "assessment": assessment,
                "status": "published",
                "created_by": admin,
            },
        )
        self.stdout.write(f"  {'✓ Created' if created else '→ Exists'}: {SAMPLE_REPORT_TITLE}")
        if report.status == "published" and report.assessment_id:
            for session in completed.filter(
                assessment_id=report.assessment_id, candidate__email__in=demo_emails
            ).select_related("assessment", "candidate"):
                if GeneratedReport.objects.filter(report=report, session=session).exists():
                    continue
                try:
                    data = generate_report_data(report, session)
                except Exception as exc:  # demo data must never break a deploy
                    self.stdout.write(f"  ! Could not generate for session {session.id}: {exc}")
                    continue
                GeneratedReport.objects.create(
                    report=report,
                    session=session,
                    candidate=session.candidate,
                    rendered_data=data,
                    status="generated",
                )
                self.stdout.write(f"  ✓ Generated sample report for {session.candidate.email}")

        solution, created = ProfilingSolution.objects.get_or_create(
            title=SAMPLE_SOLUTION_TITLE,
            defaults={
                "purpose": "A ready-made draft to explore profiling set-up.",
                "description": "Edit or duplicate this draft to try bands, mapping rules and criteria.",
                "created_by": admin,
            },
        )
        if created:
            SelectedAssessment.objects.get_or_create(solution=solution, assessment=assessment)
        self.stdout.write(f"  {'✓ Created' if created else '→ Exists'}: {SAMPLE_SOLUTION_TITLE}")
