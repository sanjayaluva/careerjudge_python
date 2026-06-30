# CareerJudge — Implementation Plan

> Living document. Updated as phases ship.

## 1. Architecture overview

```
┌────────────────────────────────────────────────────────────┐
│  Browser (candidate / counsellor / admin)                  │
│  React SPA served from Caddy static files (prod)           │
│  or Vite dev server (dev)                                  │
└────────────────────────────────────────────────────────────┘
                          │ HTTPS
                          ▼
┌────────────────────────────────────────────────────────────┐
│  Caddy (auto-TLS reverse proxy)                            │
│  - /api/*  → backend (gunicorn)                            │
│  - /*      → frontend static files                          │
│  - /ws/*   → (future) Django Channels                      │
└────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌──────────────────────┐         ┌──────────────────────────┐
│  Backend container   │         │  (Frontend static files  │
│  Django 5 + DRF      │         │   baked into Caddy image │
│  gunicorn (2 dev /   │         │   for prod; served by    │
│  4 prod workers)     │         │   Vite in dev)           │
│                      │         └──────────────────────────┘
│  Celery worker       │
│  Celery beat         │
└──────────┬───────────┘
           │
   ┌───────┴────────┬─────────────┐
   ▼                ▼             ▼
┌─────────┐  ┌──────────┐  ┌────────────────┐
│Postgres │  │  Redis   │  │ Object Storage │
│  16     │  │  7       │  │ (OCI / GCS)    │
└─────────┘  └──────────┘  └────────────────┘
```

## 2. Tech stack (locked)

| Concern | Choice | Reason |
|---|---|---|
| Backend framework | Django 5 + DRF 3.15 | Best-in-class ORM, migrations, RBAC, batteries; spec-aligned |
| Auth | SimpleJWT + django-allauth | SPA-friendly stateless tokens; activation/reset flows |
| RBAC | `django-role-permissions` + custom `ModuleRight` model | 9 roles × module-specific action rights |
| Async tasks | Celery 5 + Redis 7 | Mail, PDF report generation, training reminders |
| DB | PostgreSQL 16 | Spec-aligned; JSONField for polymorphic question data |
| Frontend framework | React 18 + Vite 5 + TypeScript 5 | Best for SPA with 21 interactive question types |
| UI library | Tailwind CSS 3 + shadcn/ui | Clean, modern, professional, accessible |
| State | TanStack Query (server) + Zustand (client) | Standard SPA pattern |
| Testing | pytest + pytest-django + factory_boy (backend); Vitest + Playwright (frontend) | Mature, covers every route + E2E |
| Lint/format | ruff + black + mypy (backend); eslint + prettier + tsc (frontend) | Modern Python/JS toolchain |
| Infra | Docker + Caddy + docker-compose | One-command deploy; auto-TLS |
| CI/CD | GitHub Actions | Free minutes; native SSH deploy |
| Dev host | GCP Compute Engine (1 vCPU/1 GB) | Already configured, domain points here |
| Prod host | OCI Ampere A1 (1 OCPU/6 GB, Always Free) | Sufficient RAM for full stack; zero cost forever |
| Dev DB | Neon Postgres free tier | External, frees GCP VM RAM, branching for tests |
| Prod DB | Postgres on OCI VM | Local = no egress latency |
| Object storage | OCI Object Storage (S3-compatible) | Free 20 GB, native to prod host |
| Container registry | GHCR (GitHub Container Registry) | Free, integrated with GitHub Actions |

## 3. Module map (10 modules)

| # | Module | Apps path | Phase | Status |
|---|---|---|---|---|
| 1 | accounts | `backend/apps/accounts/` | 1 | In progress |
| 2 | organizations | `backend/apps/organizations/` | 2 | Pending |
| 3 | question_bank | `backend/apps/question_bank/` | 2 | Pending |
| 4 | assessment | `backend/apps/assessment/` | 2 | Pending |
| 5 | career_profiling | `backend/apps/career_profiling/` | 3 | Pending |
| 6 | reporting | `backend/apps/reporting/` | 3 | Pending |
| 7 | training | `backend/apps/training/` | 4 | Pending |
| 8 | counseling | `backend/apps/counseling/` | 4 | Pending |
| 9 | cms | `backend/apps/cms/` | 4 | Pending |
| 10 | notifications | `backend/apps/notifications/` | 1 (minimal) → full in Phase 4 | In progress |

## 4. Phases

### Phase 1 — Foundation (current)

**Goal:** production-ready accounts module + working CI/CD + deployable dev environment.

- [x] Repo init, docs, git discipline
- [x] Backend skeleton (Django 5 + DRF + custom user + RBAC + JWT)
- [x] Frontend skeleton (Vite + React + TS + Tailwind + dashboard shell)
- [x] Infra (Docker, Caddy, compose)
- [x] CI/CD workflows
- [ ] `accounts` module — full implementation
  - [ ] Models: `User`, `Role`, `Permission`, `ModuleRight`, `UserProfile`, `EmailVerificationToken`, `PasswordResetToken`
  - [ ] APIs: signup, login, logout, verify-email, resend-verification, forgot-password, reset-password, me, change-password, profile update
  - [ ] Admin APIs: users CRUD, roles CRUD, permissions list, assign role, revoke role, module rights CRUD
  - [ ] Demo seeder: 1 user per role (cj_admin, corp_admin, corp_exclusive, psychometrician, sme_reviewer, trainer, group_admin, counsellor, individual)
  - [ ] Tests: every endpoint, ≥80% coverage on touched code
  - [ ] Frontend: Login, Signup, VerifyEmail, ForgotPassword, ResetPassword pages
  - [ ] Frontend: dashboard shell with role-based nav, Profile, Settings, Users, Roles, Permissions pages
  - [ ] Frontend tests: Vitest unit + Playwright E2E for auth flows
- [ ] `notifications` module — minimal: email send via SMTP/console, Celery task wrapper
- [ ] Deploy to GCP dev, verify auto-deploy works

### Phase 2 — Assessment engine

- [ ] `organizations` module — corporate/corp-exclusive/channel-partner/group management, multi-tenancy
- [ ] `question_bank` module — 21 question types, tests, sections, media
- [ ] `assessment` module — sessions, attempts, 8 scoring modes, candidate SPA

### Phase 3 — Profiling & reporting

- [ ] `career_profiling` module — config + match index + gap values + variables + blueprint + design
- [ ] `reporting` module — general + profiling reports + gap-band + PDF generation

### Phase 4 — Auxiliary modules

- [ ] `training` module
- [ ] `counseling` module
- [ ] `cms` module
- [ ] `notifications` module — full (mail templates, content generator, content delivery)

## 5. Git & deployment discipline

### Branch model

```
main (protected, deployable)
  └─ develop (integration)
       └─ feature/<module>-<scope>  (e.g. feature/accounts-jwt-auth)
       └─ fix/<module>-<scope>      (e.g. fix/accounts-token-expiry)
       └─ chore/<module>-<scope>    (e.g. chore/accounts-additive-tags)
```

### Commit convention

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `test`, `ci`, `docs`, `refactor`, `chore`, `perf`, `build`.

Scopes: module name (`accounts`, `assessment`, `infra`, `ci`, etc.).

Examples:
```
feat(accounts): add JWT login endpoint with refresh token rotation
test(accounts): add tests for signup endpoint validation
fix(accounts): handle case-insensitive email lookup
ci: add SSH deploy to GCP dev on push to main
docs: add PLAN.md and CONTRIBUTING.md
```

### Module freeze policy

Once a module ships to prod (tagged `vX.Y.0`), it is **frozen**:

- ✅ Allowed: additive changes (new endpoints, new nullable fields, new permissions)
- ❌ Forbidden: modifying or removing existing endpoints/fields/permissions
- Breaking changes require a new versioned module (e.g. `assessment_v2`) + deprecation path

Frozen modules are tracked in [`MODULE_FREEZE.md`](./MODULE_FREEZE.md).

### CI gates

Every PR must pass:
- `ruff check` + `black --check` + `mypy` (backend)
- `eslint` + `tsc --noEmit` (frontend)
- `pytest --cov` (backend, ≥80% on touched files)
- `vitest run` (frontend)
- `bandit` + `pip-audit` + `npm audit` (security)
- Build Docker images successfully

### CD triggers

- Push to `main` → deploy to **dev** (GCP CE 35.208.224.41)
- Tag `v*.*.*` → deploy to **prod** (OCI) after CI green
- Both via: SSH → `docker compose pull && up -d && python manage.py migrate`

## 6. Spec mapping

The client's 15 JSON spec files are stored read-only in `specs/cj_jsons/`. Each module's implementation references specific spec files:

| Module | Spec files |
|---|---|
| accounts | `11_SRS.json` (UC001, UC002, UC003, UC004, UC005, UC006, UC007, UC018, UC043), `09_admin_system_administration.json` |
| question_bank | `01_question_bank_creation.json`, `00_question_types_spec.json`, `00_django_model_hints.json` |
| assessment | `03_assessment_configuration.json`, `00_scoring_rules.json` |
| career_profiling | `05_profiling_configuration.json`, `00_scoring_rules.json` |
| reporting | `04_general_report_generation.json`, `06_profiling_report_generation.json`, `10_sample_profiling_report.json` |
| training | `07_training_setup_process.json` |
| counseling | `08_counseling_process.json` |
| cms | (from `11_SRS.json` — CMS Management use cases) |
| notifications | (action_service_layer in `11_SRS.json`) |
