# CareerJudge

A modern, professional career assessment, profiling, and counseling platform built with **Django 5 + DRF** (backend) and **React 18 + Vite + TypeScript + Tailwind** (frontend), deployed to **GCP Compute Engine** (dev) and **OCI Ampere A1** (prod) via **GitHub Actions SSH auto-deploy**.

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x, Django REST Framework 3.15, SimpleJWT, django-role-permissions, Celery 5, Redis 7 |
| Database | PostgreSQL 16 (Neon free tier for dev; OCI Postgres for prod) |
| Frontend | React 18, Vite 5, TypeScript 5, Tailwind CSS 3, shadcn/ui, TanStack Query, Zustand, React Router |
| Tests | pytest + pytest-django + factory_boy + coverage.py (backend); Vitest + Playwright (frontend) |
| Infra | Docker, Caddy (auto-TLS reverse proxy), docker-compose |
| CI/CD | GitHub Actions (lint → test → build → security scan → SSH deploy) |
| Hosting | GCP Compute Engine (dev, 1 vCPU/1 GB) + OCI Ampere A1 (prod, 1 OCPU/6 GB) |

## Architecture

Monorepo with two deployables:

```
careerjudge_python/
├── backend/        # Django + DRF API
├── frontend/       # React SPA
├── infra/          # Caddy, docker-compose, deploy scripts
├── specs/          # Frozen client requirement JSONs (read-only)
├── docs/           # Architecture, ADRs, module freeze log
└── .github/        # CI/CD workflows
```

**No Django admin.** The React frontend owns all user/role/permission management. A single dashboard shell renders role-aware navigation — users see only the modules they have rights to.

## Modules

The system is organized into 10 cohesive domain modules (spec-aligned). See [`PLAN.md`](./PLAN.md) and [`MODULE_FREEZE.md`](./MODULE_FREEZE.md) for the freeze policy.

1. **accounts** — auth, users, roles, permissions, profile, demo seeding (Phase 1)
2. **organizations** — corporate/group/channel-partner management (Phase 2)
3. **question_bank** — 21 question types, tests, sections, media (Phase 2)
4. **assessment** — sessions, attempts, 8 scoring modes (Phase 2)
5. **career_profiling** — profiling config + match index + gap values + variables (Phase 3)
6. **reporting** — general + profiling reports + PDF generation (Phase 3)
7. **training** — training setup, assignments (Phase 4)
8. **counseling** — counseling sessions (Phase 4)
9. **cms** — content management (Phase 4)
10. **notifications** — mail, content generator, content delivery (cross-cutting)

## Quick Start

### Backend (dev)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit DB URL, secrets
python manage.py migrate
python manage.py seed_demo  # creates 1 user per role
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

## Git Discipline

- **Branch model**: `main` (protected) ← `develop` (integration) ← `feature/<module>-<scope>`
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat(accounts): add JWT login endpoint`
- **Module freeze**: see [`MODULE_FREEZE.md`](./MODULE_FREEZE.md). Frozen modules accept additive changes only.
- **PR rules**: CI must be green (lint + tests + coverage ≥ 80% on touched modules + security scans).

## CI/CD

- Push to `main` → auto-deploy to **dev** (GCP)
- Tag `v*.*.*` → auto-deploy to **prod** (OCI) after CI passes
- Both via SSH + `docker compose pull && up -d`

## Documentation

- [`PLAN.md`](./PLAN.md) — architecture, module map, phases
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — git rules, commit conventions, testing standards
- [`MODULE_FREEZE.md`](./MODULE_FREEZE.md) — frozen module log and additive-only policy
- [`specs/`](./specs/) — frozen client requirement specs (do not modify)

## Security Notes

- All secrets via environment variables or GCP/OCI secret managers — never committed.
- JWT for API auth, httpOnly cookies for session tokens in browser.
- CORS allowlist, CSRF protection, rate-limiting on auth endpoints.
- `bandit`, `pip-audit`, `npm audit` run on every CI build.
