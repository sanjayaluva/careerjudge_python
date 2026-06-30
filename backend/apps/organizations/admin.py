"""Django admin registrations.

Note: CareerJudge does NOT use Django admin for user-facing UI.
All management is done via the React frontend. The admin/ route
is kept only for superuser emergency access and is permission-gated.
"""

from django.contrib import admin  # noqa: F401
