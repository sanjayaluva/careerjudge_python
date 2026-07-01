# Phase 1 Gap Analysis — Requirements vs Implementation

> Generated 2026-07-01. Compares the SRS (`specs/11_SRS.json`) + module specs against what's actually implemented in Phase 1.

## Legend

- ✅ **Implemented** — fully working, tested
- ⚠️ **Partial** — basic version works, needs enhancement
- ❌ **Not implemented** — planned for later phases
- 🔄 **Placeholder** — UI exists but routes to "coming soon" page

---

## Module 1: accounts (Phase 1) — ✅ 90% complete

### SRS Use Cases

| UC# | Title | Status | Notes |
|---|---|---|---|
| UC001 | Sign up | ✅ | Email verification flow, activation link, 24h expiry |
| UC002 | Add user (admin) | ✅ | Admin can create users, assign role, auto-generate password |
| UC003 | Edit user (admin) | ✅ | Admin can edit users; email uniqueness excludes self |
| UC004 | Delete user (admin) | ✅ | CJ Admin cannot delete individual users (403 per spec) |
| UC005 | Manage profile | ✅ | User can update full_name, phone, profile fields |
| UC006 | View profile | ✅ | /api/me/ returns full user + profile |
| UC007 | Login | ✅ | JWT access + refresh tokens, rotation, blacklisting |
| UC018 | Role management | ✅ | 10 system roles (frozen) + custom roles with permission selector |
| UC043 | Add user (channel partner) | ❌ | Channel partner feature is Phase 2 (organizations module) |

### Features implemented

- ✅ Email-based auth (no username)
- ✅ JWT with sliding session (60 min access, 30 day refresh)
- ✅ Email verification (UC001 activation flow)
- ✅ Password reset (forgot-password → email link → reset)
- ✅ Change password (authenticated user)
- ✅ 10 system roles: cj_admin, corp_admin, corp_exclusive, psychometrician, sme, reviewer, trainer, group_admin, counsellor, individual
- ✅ Custom roles with base_role inheritance + permission selector
- ✅ Module-specific RBAC (ModuleRight: role × module × action)
- ✅ SME vs Reviewer split (SME creates/edits/deletes own questions; Reviewer reviews/approves/rejects)
- ✅ User CRUD (admin)
- ✅ Role CRUD (admin — system roles read-only, custom roles full CRUD)
- ✅ Permission assign/remove (custom roles only)
- ✅ Demo seeder (10 users + 1 superuser + permissions)
- ✅ 87 backend tests, 81% coverage
- ✅ 28 frontend tests

### What's NOT in accounts but planned

- ❌ **OAuth/social login** (Google, LinkedIn) — not in SRS, defer
- ❌ **2FA/MFA** — not in SRS, defer
- ❌ **Login attempt throttling** — throttling configured but needs IP-based lockout
- ❌ **Password history** (prevent reuse) — not in SRS
- ❌ **Email change with verification** — currently email is read-only per UC005

---

## Module 2: organizations (Phase 2) — ❌ Not started

### SRS Use Cases

| UC# | Title | Status |
|---|---|---|
| UC009-UC017 | Corporate/group/channel-partner management | ❌ |

**Planned**: corporate entities, groups, channel partners, multi-tenancy

---

## Module 3: question_bank (Phase 2) — ❌ Not started

### Spec source: `01_question_bank_creation.json`, `00_question_types_spec.json`

| Feature | Status |
|---|---|
| 21 question types (MCQ, FITB, Match, Grid, Hotspot, Rank, Rating, Forced-choice) | ❌ |
| Test/Section/Question/MediaFile/FlashItem models | ❌ |
| Question review workflow (SME creates → Reviewer approves/rejects) | ❌ |
| Question bank CRUD API | ❌ |
| Question import/export | ❌ |

---

## Module 4: assessment (Phase 2) — ❌ Not started

### Spec source: `03_assessment_configuration.json`, `00_scoring_rules.json`

| Feature | Status |
|---|---|
| Test session (create/suspend/resume/complete) | ❌ |
| 8 scoring modes (BINARY, BINARY_FUZZY, PARTIAL, NEGATIVE, RANK, RANK_RATE, RATING, FORCED_CHOICE) | ❌ |
| Candidate assessment player (SPA with ms-precision timing) | ❌ |
| Assessment configuration (test assembly, section ordering) | ❌ |

---

## Module 5: career_profiling (Phase 3) — ❌ Not started

### Spec source: `05_profiling_configuration.json`

| Feature | Status |
|---|---|
| Profiling configuration | ❌ |
| Profile Match Index Band | ❌ |
| Gap Values Calculation | ❌ |
| Variables configuration for Career Match List | ❌ |
| Career Profiling Report Blue Print | ❌ |
| Career Profiling Design | ❌ |

---

## Module 6: reporting (Phase 3) — ❌ Not started

### Spec source: `04_general_report_generation.json`, `06_profiling_report_generation.json`

| Feature | Status |
|---|---|
| General report generation | ❌ |
| Profiling report generation | ❌ |
| Gap Band calculation | ❌ |
| PDF generation (WeasyPrint) | ❌ |
| Report templates | ❌ |

---

## Module 7: training (Phase 4) — ❌ Not started

### Spec source: `07_training_setup_process.json`

| Feature | Status |
|---|---|
| Training setup | ❌ |
| Training assignments | ❌ |
| Training progress tracking | ❌ |

---

## Module 8: counseling (Phase 4) — ❌ Not started

### Spec source: `08_counseling_process.json`

| Feature | Status |
|---|---|
| Counseling session scheduling | ❌ |
| Counseling notes | ❌ |
| Counselor-candidate matching | ❌ |

---

## Module 9: cms (Phase 4) — ❌ Not started

| Feature | Status |
|---|---|
| Content management (pages, banners) | ❌ |
| CMS CRUD API | ❌ |

---

## Module 10: notifications (Phase 1 minimal → Phase 4 full) — ⚠️ 20% complete

| Feature | Status | Notes |
|---|---|---|
| Email send (console backend in dev) | ✅ | Works for signup verification, password reset |
| Email send (SMTP in prod) | ✅ | Configured, needs SMTP creds |
| Celery async tasks | ⚠️ | Eager mode in dev; worker container in prod compose |
| Mail templates | ❌ | Plain text only; HTML templates needed |
| Content generator | ❌ | Phase 4 |
| Content delivery | ❌ | Phase 4 |
| In-app notifications | ❌ | Phase 4 |

---

## Frontend — ✅ 85% complete (for Phase 1 scope)

### Pages implemented

| Page | Status | Notes |
|---|---|---|
| Login | ✅ | JWT, validation, error display |
| Signup | ✅ | Email verification flow |
| Verify email | ✅ | Token-based activation |
| Forgot password | ✅ | Silent success (no email leakage) |
| Reset password | ✅ | Token-based reset |
| Dashboard | ✅ | Role-aware module cards (filtered by user role) |
| Profile | ✅ | Edit basic info + profile details (2 tabs) |
| Settings | ✅ | Change password |
| Users (admin) | ✅ | List + create + edit + delete + assign role + view page |
| User view (admin) | ✅ | Read-only profile-style view |
| Roles (admin) | ✅ | System roles (frozen) + custom roles + permission selector |
| Permissions (admin) | ✅ | Read-only permission catalog |
| 404 Not Found | ✅ | |
| Placeholder pages | 🔄 | organizations, question_bank, assessment, career_profiling, reports, training, counseling, cms → "coming soon" |

### Frontend features

- ✅ Role-based sidebar navigation (filtered by MODULE_VISIBILITY)
- ✅ Protected routes (redirect to /login if not authed)
- ✅ Admin-only routes (redirect to /dashboard?denied if no permission)
- ✅ JWT auto-refresh on 401 (axios interceptor)
- ✅ TanStack Query for server state (caching, invalidation)
- ✅ Zustand for auth state (localStorage persistence)
- ✅ Form validation (react-hook-form + zod)
- ✅ Loading states (Spinner)
- ✅ Error states (Alert)
- ✅ Empty states
- ✅ Pagination + search + role filter on Users page
- ✅ Responsive (mobile sidebar, stacking forms)
- ✅ Accessibility (labels, aria, focus rings)
- ✅ Production build (465 KB JS, 143 KB gzipped)

---

## Infrastructure — ✅ 95% complete

| Component | Status | Notes |
|---|---|---|
| Backend Docker image | ✅ | Multi-stage, Python 3.12-slim, gunicorn |
| Frontend Docker image | ✅ | Multi-stage, Node 20 → nginx |
| Caddy reverse proxy | ✅ | Auto-TLS, /api/* → backend, /* → Vercel |
| docker-compose (dev) | ✅ | backend + caddy (frontend optional via --profile) |
| docker-compose (prod) | ✅ | full stack: backend + db + redis + celery + caddy |
| GitHub Actions CI | ✅ | lint + test + coverage + security + docker build |
| GitHub Actions CD (dev) | ✅ | SSH deploy on push to main (needs secrets) |
| GitHub Actions CD (prod) | ✅ | SSH deploy on tag (needs secrets + OCI VM) |
| Vercel frontend deploy | ✅ | Auto-deploy on push to main |
| Neon Postgres (dev) | ✅ | External, free tier, seeded |
| Dependabot | ✅ | Weekly pip + npm + Docker + Actions updates |

---

## Summary

| Module | Phase | Completion |
|---|---|---|
| accounts | 1 | ✅ 90% |
| notifications | 1 (minimal) | ⚠️ 20% |
| organizations | 2 | ❌ 0% |
| question_bank | 2 | ❌ 0% |
| assessment | 2 | ❌ 0% |
| career_profiling | 3 | ❌ 0% |
| reporting | 3 | ❌ 0% |
| training | 4 | ❌ 0% |
| counseling | 4 | ❌ 0% |
| cms | 4 | ❌ 0% |
| **Frontend (Phase 1)** | 1 | ✅ 85% |
| **Infrastructure** | 1 | ✅ 95% |

**Phase 1 is production-ready for the accounts/admin/auth scope.** Phase 2 (question_bank + assessment) is the next priority — it's the core value of the platform.
