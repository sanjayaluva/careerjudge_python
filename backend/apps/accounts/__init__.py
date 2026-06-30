"""Accounts module — auth, RBAC, profile, demo seeding.

Spec source: 11_SRS.json (UC001-UC006, UC007, UC018, UC043),
              09_admin_system_administration.json

Models:
    User            — custom user (email-based, no username)
    UserProfile     — extended profile fields (gender, dob, mobile, etc.)
    Role            — named role with module-specific rights
    ModuleRight     — action-wise permission per module
    EmailVerificationToken — single-use token for email verification
    PasswordResetToken     — single-use token for password reset

APIs (see urls_auth.py, urls_me.py, urls_admin.py):
    POST /api/auth/signup
    POST /api/auth/login
    POST /api/auth/logout
    POST /api/auth/token/refresh
    POST /api/auth/verify-email
    POST /api/auth/resend-verification
    POST /api/auth/forgot-password
    POST /api/auth/reset-password
    GET  /api/me/                — current user
    PATCH /api/me/               — update profile
    POST /api/me/change-password
    GET  /api/accounts/users/    — list (admin)
    POST /api/accounts/users/    — create (admin)
    GET  /api/accounts/users/<id>/   — retrieve (admin)
    PATCH /api/accounts/users/<id>/  — update (admin)
    DELETE /api/accounts/users/<id>/ — delete (admin)
    GET  /api/accounts/roles/
    POST /api/accounts/roles/
    GET  /api/accounts/roles/<id>/
    POST /api/accounts/roles/<id>/assign-permission/
    POST /api/accounts/users/<id>/assign-role/
"""
