"""Top-level pytest config — ensures Django is set up correctly."""
import os
import django


def pytest_configure(config):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    django.setup()
