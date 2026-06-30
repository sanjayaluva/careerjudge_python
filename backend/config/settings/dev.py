"""Dev settings — local development, debug enabled.

Defaults to SQLite + LocMemCache so a fresh checkout works without
Postgres or Redis. To use production-like services, set DATABASE_URL
and REDIS_URL in .env.
"""

import os

from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "*"])

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CORS_ALLOW_ALL_ORIGINS = True

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# If no DATABASE_URL is set, fall back to SQLite for friction-free local dev
_db_url = os.environ.get("DATABASE_URL", "")
if not _db_url:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),  # noqa: F405
        }
    }

# Use LocMemCache in dev unless REDIS_URL is explicitly set and reachable.
_redis_url = os.environ.get("REDIS_URL", "")
if not _redis_url or _redis_url.startswith("redis://localhost"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "careerjudge-dev",
        }
    }
    # Celery in eager mode (no broker needed)
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
