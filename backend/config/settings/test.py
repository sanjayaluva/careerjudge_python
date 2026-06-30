"""Test settings — used by pytest-django.

Uses SQLite for fast tests without a Postgres dependency.
Set DATABASE_URL=postgres://... to override for prod-like tests.
"""

import os

from .dev import *  # noqa: F403

# Force SQLite for tests unless explicitly overridden
_db_url = os.environ.get("DATABASE_URL", "")
if not _db_url or "postgres" not in _db_url:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Disable throttling in tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        "anon": None,
        "user": None,
        "auth": None,
    },
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Use LocMemCache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "careerjudge-test",
    }
}
