"""Top-level pytest config — ensures Django is set up correctly."""

import os

import django
import pytest


def pytest_configure(config):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    django.setup()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Start every test from an empty roles table, as the tests expect.

    accounts/0015 creates the system roles with their rights so a fresh
    production database works without seed_demo (code review, 3 Oct 2026);
    tests set up the roles they need themselves."""
    with django_db_blocker.unblock():
        from apps.accounts.models import ModuleRight, Role

        ModuleRight.objects.all().delete()
        Role.objects.all().delete()
