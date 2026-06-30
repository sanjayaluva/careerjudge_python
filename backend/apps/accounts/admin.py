"""Django admin registrations.

CareerJudge does NOT use Django admin for user-facing UI.
All user/role/permission management is done via the React frontend.
The admin/ route is kept only for superuser emergency access.
"""

# Register minimal read-only admin for emergency superuser access.
# Real user management happens in the frontend.
