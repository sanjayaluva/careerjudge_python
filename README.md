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
├── docs/           # All project documentation (module specs, guides, plans)
└── .github/        # CI/CD workflows
```

**No Django admin.** The React frontend owns all user/role/permission management. A single dashboard shell renders role-aware navigation — users see only the modules they have rights to.

## Modules

The system is organized into 10 cohesive domain modules (spec-aligned). See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for current status and [docs/MODULE_FREEZE.md](docs/MODULE_FREEZE.md) for the freeze policy.

1. **accounts** — auth, users, roles, permissions, profile, demo seeding ✅ Frozen v1.1.0
2. **organizations** — corporate/group/channel-partner management ✅ Frozen v1.0.0
3. **question_bank** — 21 question types, 9 scoring modes, 3-stage review workflow 🔧 Active
4. **assessment** — sessions, attempts, 8 scoring modes 📋 Planned
5. **career_profiling** — profiling config + match index + gap values + variables 📋 Planned
6. **reporting** — general + profiling reports + PDF generation 📋 Planned
7. **training** — training setup, assignments 📋 Planned
8. **counseling** — counseling sessions 📋 Planned
9. **cms** — content management 📋 Planned
10. **notifications** — mail, content generator, content delivery 📋 Planned

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

### Demo credentials

After `seed_demo`, login with any of these (password: `Demo@1234`):
- `cj.admin@demo.careerjudge.pp.ua` — CareerJudge Admin
- `sme@demo.careerjudge.pp.ua` — SME (can create/edit questions)
- `reviewer@demo.careerjudge.pp.ua` — Reviewer (can review questions)
- `psychometrician@demo.careerjudge.pp.ua` — Psychometrician (can confirm questions)

## Git Discipline

- **Branch model**: `main` (protected) ← `develop` (integration) ← `feature/<module>-<scope>`
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat(accounts): add JWT login endpoint`
- **Module freeze**: see [docs/MODULE_FREEZE.md](docs/MODULE_FREEZE.md). Frozen modules accept additive changes only.
- **PR rules**: CI must be green (lint + tests + coverage ≥ 80% on touched modules + security scans).

## CI/CD

- Push to `main` → auto-deploy to **dev** (GCP) at https://careerjudge.pp.ua
- Tag `v*.*.*` → auto-deploy to **prod** (OCI) after CI passes
- Both via SSH + `docker compose pull && up -d`

## Documentation

All documentation lives in the [`docs/`](docs/) folder. Key documents:

- [docs/README.md](docs/README.md) — Documentation index
- [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) — Current development status and next priorities
- [docs/ARCHITECTURE_PLAN.md](docs/ARCHITECTURE_PLAN.md) — Architecture and phased development plan
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — Git rules, commit conventions, testing standards
- [docs/MODULE_FREEZE.md](docs/MODULE_FREEZE.md) — Frozen module log and additive-only policy
- [docs/modules/](docs/modules/) — Per-module documentation (accounts, organizations, question_bank)
- [specs/](specs/) — Frozen client requirement specs (do not modify)

## Security Notes

- All secrets via environment variables or GCP/OCI secret managers — never committed.
- JWT for API auth (60-min access, 30-day refresh, proactive refresh before expiry).
- CORS allowlist, CSRF protection, rate-limiting on auth endpoints.
- `bandit`, `pip-audit`, `npm audit` run on every CI build.
