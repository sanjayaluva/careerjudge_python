"""Tests for accounts data migrations (grant_perms-style RunPython functions).

These call the migration functions directly against the real app registry —
the same pattern implicitly exercised by `python manage.py migrate` — rather
than spinning up a full MigrationExecutor, since none of these migrations
change model schema (only data).
"""

import importlib

import pytest
from django.apps import apps

from apps.accounts.models import ModuleRight, Role

_migration = importlib.import_module(
    "apps.accounts.migrations.0010_psychometrician_reporting_perms"
)
grant_perms = _migration.grant_perms
revoke_perms = _migration.revoke_perms


@pytest.mark.django_db
class TestPsychometricianReportingPermsMigration:
    def test_grants_reporting_generate_report(self):
        role = Role.objects.create(name="psychometrician", is_system=True, is_frozen=True)
        grant_perms(apps, None)
        assert ModuleRight.objects.filter(
            role=role, module="reporting", action="generate_report"
        ).exists()

    def test_idempotent(self):
        role = Role.objects.create(name="psychometrician", is_system=True, is_frozen=True)
        grant_perms(apps, None)
        grant_perms(apps, None)
        assert (
            ModuleRight.objects.filter(
                role=role, module="reporting", action="generate_report"
            ).count()
            == 1
        )

    def test_noop_when_role_missing(self):
        # Should not raise even though no psychometrician role exists yet.
        grant_perms(apps, None)
        assert not ModuleRight.objects.filter(module="reporting", action="generate_report").exists()

    def test_revoke_removes_the_grant(self):
        role = Role.objects.create(name="psychometrician", is_system=True, is_frozen=True)
        grant_perms(apps, None)
        revoke_perms(apps, None)
        assert not ModuleRight.objects.filter(
            role=role, module="reporting", action="generate_report"
        ).exists()
