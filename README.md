# CareerJudge

A modern, professional career assessment, profiling, and counseling platform built with **Django 5 + DRF** (backend) and **React 18 + Vite + TypeScript + Tailwind** (frontend), deployed to **any standard cloud VM provider** via **GitHub Actions SSH auto-deploy**.

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x, Django REST Framework 3.15, SimpleJWT, django-role-permissions, Celery 5, Redis 7 |
| Database | PostgreSQL 16 (managed Postgres service for dev; self-hosted on prod VM) |
| Frontend | React 18, Vite 5, TypeScript 5, Tailwind CSS 3, shadcn/ui, TanStack Query, Zustand, React Router |
| Tests | pytest + pytest-django + factory_boy + coverage.py (backend — 247 tests, 87% coverage); Vitest + Playwright (frontend — 30 unit tests) |
| Infra | Docker (multi-stage builds + volume mounts for fast dev redeploy), Caddy (auto-TLS reverse proxy), docker-compose |
| CI/CD | GitHub Actions (lint → test → build → security scan → SSH deploy) |
| Hosting | Cloud VM (dev) + Cloud VM (prod) — any standard provider |

## Architecture

Monorepo with two deployables:

```
careerjudge_python/
├── backend/        # Django + DRF API
├── frontend/       # React SPA
├── infra/          # Caddy, docker-compose, deploy scripts
├── specs/          # Frozen client requirement JSONs (read-only)
├── docs/           # All project documentation (module specs, guides, plans)
└── .github/        # CI/CD workflows
```

**No Django admin.** The React frontend owns all user/role/permission management. A single dashboard shell renders role-aware navigation — users see only the modules they have rights to.

## Modules

The system is organized into 11 cohesive domain modules (spec-aligned). See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for current status and [docs/MODULE_FREEZE.md](docs/MODULE_FREEZE.md) for the freeze policy.

| # | Module | Status | Tests | Docs |
|---|---|---|---|---|
| 1 | **accounts** — auth, users, roles, permissions, profile | ✅ Frozen v1.1.0 | 83 tests, 84% coverage | [accounts.md](docs/modules/accounts.md) |
| 2 | **organizations** — corporate/group/channel-partner management | ✅ Frozen v1.0.0 | 82% coverage | [organizations.md](docs/modules/organizations.md) |
| 3 | **question_bank** — 21 question types, 9 scoring modes, 3-stage review workflow | 🔧 Active v1.0.0-pre | 53 tests | [question_bank.md](docs/modules/question_bank.md) |
| 4 | **assessment** — sessions, attempts, 9-mode scoring engine, candidate player | 🔧 Active v1.0.0-pre | 76 tests | [assessment.md](docs/modules/assessment.md) |
| 5 | **career_profiling** — profiling config + match index + gap values + variables | 📋 Planned | — | — |
| 6 | **reporting** — general + profiling reports + PDF generation | 📋 Planned | — | — |
| 7 | **training** — training setup, assignments | 📋 Planned | — | — |
| 8 | **counseling** — counseling sessions | 📋 Planned | — | — |
| 9 | **cms** — content management | 📋 Planned | — | — |
| 10 | **notifications** — mail, content generator, content delivery | 📋 Planned | — | — |
| 11 | **infrastructure** — Docker, Caddy, CI/CD, deploy scripts | ✅ Complete | — | [infrastructure/](docs/infrastructure/) |

### Server Requirements

The application runs on any standard cloud VM provider. Minimum recommended specs:

| Environment | vCPU | RAM | Disk | Notes |
|---|---|---|---|---|
| Dev | 1 | 1 GB | 20 GB | Backend + Caddy; Postgres external |
| Prod (small) | 2 | 4 GB | 40 GB | Full stack: backend + Postgres + Redis + Celery |
| Prod (recommended) | 4 | 8 GB | 80 GB | Headroom for growth + reporting workloads |

Compatible with any Linux distribution that supports Docker (Ubuntu 22.04+, Debian 12+, RHEL 9+). No vendor lock-in — deployment is fully containerized via Docker Compose.

## Quick Start

### Backend (dev)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit DB URL, secrets
python manage.py migrate
python manage.py seed_demo  # creates 1 user per role + superuser
python manage.py runserver
```

### Frontend (dev)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

### Full stack with Docker

```bash
cp .env.example .env
docker compose -f infra/docker/docker-compose.dev.yml up --build
```

For code-only changes (no requirements.txt change), use the fast volume-mount deploy — ~15 seconds instead of a full image rebuild:

```bash
infra/deploy/deploy-dev.sh
```

See [docs/FAST_DEV_WORKFLOW.md](docs/FAST_DEV_WORKFLOW.md) for details.

## Demo Credentials

`python manage.py seed_demo` creates **11 demo users (one per system role)** plus a superuser. All demo users share the password `Demo@1234`.

| # | Role | Email | Sees in sidebar |
|---|---|---|---|
| 1 | CareerJudge Admin | `cj.admin@demo.careerjudge.pp.ua` | All modules (full access) |
| 2 | Corporate Admin | `corp.admin@demo.careerjudge.pp.ua` | Dashboard, Profile, Users, Organizations, Assessments, Reports, Training |
| 3 | Corporate Exclusive | `corp.exclusive@demo.careerjudge.pp.ua` | Dashboard, Profile, Users, Organizations, Assessments, Reports |
| 4 | Psychometrician | `psychometrician@demo.careerjudge.pp.ua` | Dashboard, Profile, Question Bank, Assessments, Career Profiling, Reports |
| 5 | SME (Subject Matter Expert) | `sme@demo.careerjudge.pp.ua` | Dashboard, Profile, Question Bank, Assessments |
| 6 | Reviewer | `reviewer@demo.careerjudge.pp.ua` | Dashboard, Profile, Question Bank, Assessments |
| 7 | Trainer | `trainer@demo.careerjudge.pp.ua` | Dashboard, Profile, Assessments, Training |
| 8 | Group Admin | `group.admin@demo.careerjudge.pp.ua` | Dashboard, Profile, Organizations, Assessments |
| 9 | Counsellor | `counsellor@demo.careerjudge.pp.ua` | Dashboard, Profile, Assessments, Career Profiling, Reports, Counseling |
| 10 | Channel Partner | `channel.partner@demo.careerjudge.pp.ua` | Dashboard, Profile, Users, Organizations, Assessments, Reports |
| 11 | Individual | `individual@demo.careerjudge.pp.ua` | Dashboard, Profile, Assessments, Career Profiling, Reports, Training, Counseling |

**Superuser** (emergency Django admin access — not for normal use):
- Email: `superuser@careerjudge.pp.ua`
- Password: `Su@12345678`

### Role-specific permissions at a glance

| Role | Question Bank | Assessment | Users | Organizations | Reports |
|---|---|---|---|---|---|
| cj_admin | view/add/change/delete/approve/reject/review | view/add/change/delete | full | full | view + generate |
| corp_admin | — | view/add | view/add/change | view/change | view + generate |
| corp_exclusive | — | view/add | view/add/change | view | view + generate |
| psychometrician | view/add/change/review | view | — | — | view |
| sme | view/add/change/delete/request_delete (own only) | view | — | — | — |
| reviewer | view/review/approve/reject (no edit) | view | — | — | — |
| trainer | — | view | view | — | — |
| group_admin | — | view + assign | view | view | — |
| counsellor | — | view | view | — | view |
| channel_partner | — | view/add | view/add/change | view/change | view + generate |
| individual | — | view (take assessments) | — | — | view (own only) |

See `backend/apps/accounts/management/commands/seed_demo.py` for the authoritative permission matrix.

## Git Discipline

- **Branch model**: `main` (protected) ← `develop` (integration) ← `feature/<module>-<scope>`
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat(accounts): add JWT login endpoint`
- **Module freeze**: see [docs/MODULE_FREEZE.md](docs/MODULE_FREEZE.md). Frozen modules accept additive changes only.
- **PR rules**: CI must be green (lint + tests + coverage ≥ 80% on touched modules + security scans).

## CI/CD

- Push to `main` → auto-deploy to **dev** server at https://careerjudge.pp.ua
- Tag `v*.*.*` → auto-deploy to **prod** server after CI passes
- Both via SSH + `docker compose pull && up -d`
- Docker image builds only run on tags or `workflow_dispatch` — code-only pushes use volume mounts for ~15s deploys

## Documentation

All documentation lives in the [`docs/`](docs/) folder. Key documents:

- [docs/README.md](docs/README.md) — Documentation index
- [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) — Current development status and next priorities
- [docs/ARCHITECTURE_PLAN.md](docs/ARCHITECTURE_PLAN.md) — Architecture and phased development plan
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — Git rules, commit conventions, testing standards
- [docs/MODULE_FREEZE.md](docs/MODULE_FREEZE.md) — Frozen module log and additive-only policy
- [docs/FAST_DEV_WORKFLOW.md](docs/FAST_DEV_WORKFLOW.md) — Volume-mount fast deploy workflow
- [docs/modules/](docs/modules/) — Per-module documentation
  - [accounts.md](docs/modules/accounts.md) — Auth, users, roles, permissions
  - [organizations.md](docs/modules/organizations.md) — Corporate/group/channel-partner management
  - [question_bank.md](docs/modules/question_bank.md) — 21 question types, 9 scoring modes, review workflow
  - [assessment.md](docs/modules/assessment.md) — Sessions, scoring engine, candidate player
- [specs/](specs/) — Frozen client requirement specs (do not modify)

## Testing

| Layer | Tooling | Count | Coverage |
|---|---|---|---|
| Backend unit tests | pytest + pytest-django + factory_boy | 247 tests | 87% |
| Frontend unit tests | Vitest + React Testing Library | 30 tests | — |
| Frontend E2E | Playwright (specs in `frontend/e2e/`) | auth-login, auth-signup, auth-logout | — |
| Lint | ruff + black (backend); eslint + tsc (frontend) | — | — |
| Security | bandit + pip-audit (backend); npm audit (frontend) | — | — |

Run locally:

```bash
# Backend
cd backend && source .venv/bin/activate
python -m pytest apps/ --cov=apps --cov=core --cov-report=term-missing --cov-fail-under=80

# Frontend
cd frontend
npm run typecheck && npm run lint && npm run test && npm run build
```

## Security Notes

- All secrets via environment variables or cloud secret managers — never committed.
- JWT for API auth (60-min access, 30-day refresh, rotation + blacklist, proactive refresh before expiry).
- CORS allowlist, CSRF protection, rate-limiting on auth endpoints.
- `bandit`, `pip-audit`, `npm audit` run on every CI build.

## License

Proprietary — CareerJudge. All rights reserved.
