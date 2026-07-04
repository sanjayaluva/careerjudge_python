# Accounts Module — v1.1.0 (Frozen)

> **Frozen since**: 2026-07-01 (v1.0.0), additive updates v1.1.0 (2026-07-03)
> **Version**: v1.1.0
> **Phase**: 1 (complete)
> **Test coverage**: 83 tests, 84% coverage

## Overview

The accounts module handles user authentication, authorization (RBAC), profile management, and role/permission administration. It is the foundation module — all other modules depend on it for user identity and access control.

## Version History

### v1.1.0 (2026-07-03) — Additive updates (still frozen-safe)

- **Channel Partner role**: Added `channel_partner` as the 11th system role per admin spec section 2.1. Includes `channel_partner_agreement_id` and `contract_period` profile fields.
- **Scoped individual user deletion**: `cj_admin` can delete any individual user; org admins can delete individuals within their org only; others get 403. Prevents accidental cross-org deletion.
- **Bulk user upload**: CSV upload endpoint (`POST /api/accounts/users/bulk-upload/`) + template download (`GET /api/accounts/users/bulk-upload/template/`). Skips comment rows, handles duplicates gracefully.
- **Role-specific profile fields**: Per SRS pages 8-22 — individual (occupation, education), professional (PAN, bank details), channel_partner (agreement ID, contract period).
- **JWT session improvements**: Access token TTL increased to 60 min (was 15 min). Refresh token TTL 30 days. Proactive refresh before expiry (frontend axios interceptor refreshes 5 min before expiry).
- **SME/Reviewer role split**: Split the combined `sme_reviewer` role into distinct `sme` and `reviewer` roles per client clarification. SME creates/edits/deletes own questions; Reviewer reviews/approves/rejects.
- **Demo seeding**: 11 demo users (one per role) + 1 superuser, all with password `Demo@1234`.

### v1.0.0 (2026-07-01) — Initial freeze

- Custom email-based User model with JWT auth (SimpleJWT)
- 10 system roles + custom roles with base_role inheritance
- Module-level RBAC (Role × Module × Action permissions)
- Email verification + password reset flows
- User CRUD with role assignment
- Role CRUD (system roles frozen, custom roles editable)
- Permission assignment/removal
- Demo data seeding (`seed_demo` management command)

## Public API (contractually stable)

### Auth endpoints (public — no auth required)

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/signup` | Create account (sends verification email) |
| POST | `/api/auth/login` | Login (returns JWT access + refresh) |
| POST | `/api/auth/logout` | Logout (blacklists refresh token) |
| POST | `/api/auth/token/refresh` | Rotate refresh token |
| POST | `/api/auth/verify-email` | Verify email via token |
| POST | `/api/auth/resend-verification` | Resend verification email |
| POST | `/api/auth/forgot-password` | Request password reset email |
| POST | `/api/auth/reset-password` | Reset password via token |

### Current user endpoints (auth required)

| Method | Path | Description |
|---|---|---|
| GET | `/api/me/` | Get current user + profile |
| PATCH | `/api/me/` | Update full_name, phone, profile fields |
| POST | `/api/me/change-password` | Change password |

### Admin endpoints (auth + accounts module rights required)

| Method | Path | Description |
|---|---|---|
| GET | `/api/accounts/users/` | List users (paginated, searchable) |
| POST | `/api/accounts/users/` | Create user |
| GET | `/api/accounts/users/<id>/` | Retrieve user |
| PATCH | `/api/accounts/users/<id>/` | Update user |
| DELETE | `/api/accounts/users/<id>/` | Delete user (not individual role) |
| POST | `/api/accounts/users/<id>/assign-role` | Assign role to user |
| GET | `/api/accounts/roles/` | List roles (system + custom) |
| POST | `/api/accounts/roles/` | Create custom role |
| GET | `/api/accounts/roles/<id>/` | Retrieve role |
| PATCH | `/api/accounts/roles/<id>/` | Update role description (custom only) |
| DELETE | `/api/accounts/roles/<id>/` | Delete custom role |
| POST | `/api/accounts/roles/<id>/assign-permission` | Add permission (custom only) |
| POST | `/api/accounts/roles/<id>/remove-permission` | Remove permission (custom only) |

### Health endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health/` | Liveness probe |
| GET | `/api/health/db/` | Database readiness probe |

## Models

### User (custom, email-based)
- `email` (unique, normalized)
- `full_name`
- `role` (FK to Role, nullable)
- `is_email_verified`
- `is_trial_user`
- `phone`
- `is_active`, `is_staff`, `is_superuser`
- `created_at`, `updated_at`

### Role
- `name` (unique — system roles use codes like `cj_admin`; custom roles use any name)
- `description`
- `is_system` (True for 10 built-in roles — immutable)
- `is_frozen` (True for system roles — permissions cannot change)
- `base_role` (FK to self — custom roles inherit from a system role)
- `created_at`, `updated_at`

### ModuleRight
- `role` (FK to Role)
- `module` (choices: accounts, organizations, question_bank, assessment, etc.)
- `action` (choices: view, add, change, delete, approve, reject, review, assign, export, generate_report, request_delete)
- `unique_together`: (role, module, action)

### UserProfile
- `user` (OneToOne to User)
- `gender` (male, female, other, prefer_not_to_say)
- `date_of_birth`
- `mobile`
- `avatar`
- `address_line1`, `address_line2`, `city`, `state`, `country`, `postal_code`
- `bio`

### EmailVerificationToken
- `user` (FK to User)
- `token` (UUID, unique)
- `expires_at` (24h)
- `used_at`

### PasswordResetToken
- `user` (FK to User)
- `token` (UUID, unique)
- `expires_at` (1h)
- `used_at`

## 10 System Roles (frozen)

| Code | Label | Key Permissions |
|---|---|---|
| cj_admin | CareerJudge Admin | All modules — full CRUD |
| corp_admin | Corporate Admin | Users, Organizations, Assessment, Reporting, Training |
| corp_exclusive | Corporate Exclusive | Users, Organizations, Assessment, Reporting |
| psychometrician | Psychometrician | Question Bank (CRUD + review), Assessment, Reporting |
| sme | SME (Subject Matter Expert) | Question Bank (CRUD own + request_delete), Assessment |
| reviewer | Reviewer | Question Bank (review, approve, reject), Assessment |
| trainer | Trainer | Training (CRUD), Users (view), Assessment |
| group_admin | Group Admin | Users (view), Assessment (assign), Organizations |
| counsellor | Counsellor | Counseling (CRUD), Users (view), Assessment, Reporting |
| individual | Individual | Assessment (take), Reporting (own) |

## Custom Roles

Admins can create custom roles with:
- Unique name (cannot clash with system role names)
- Optional base_role (system role to inherit permissions from — inherited permissions are immutable)
- Custom permissions (addable/removable via permission selector)
- Description

## JWT Configuration

- Access token TTL: 60 minutes (default, configurable via `JWT_ACCESS_TTL_MINUTES`)
- Refresh token TTL: 30 days (default, configurable via `JWT_REFRESH_TTL_DAYS`)
- Rotation: refresh tokens rotate on use (old one blacklisted)
- Auto-refresh: frontend axios interceptor handles 401 → refresh → retry

## Additive changes allowed

After v1.0.0 freeze, the following are allowed without breaking the contract:
- New optional fields on User/UserProfile (nullable, via migration)
- New endpoints under new URL paths
- New permissions/actions
- New system roles (is_system=True) — but existing 10 cannot be modified

## Breaking changes (require v2.0.0)

- Removing/renaming endpoints
- Changing response schemas
- Removing/renaming model fields
- Changing JWT token structure
- Changing the 10 system role names/permissions
