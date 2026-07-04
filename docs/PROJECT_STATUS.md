# Project Status — CareerJudge

> **Last updated**: 2026-07-04
> **Current phase**: Phase 2 (Question Bank — in progress)

## Completed Modules

### Phase 1 — Foundation (Complete)

| Module | Version | Status | Tests | Docs |
|---|---|---|---|---|
| Accounts | v1.1.0 | ✅ Frozen | 83 tests, 84% coverage | [accounts.md](modules/accounts.md) |
| Organizations | v1.0.0 | ✅ Frozen | 82% coverage | [organizations.md](modules/organizations.md) |
| Infrastructure | — | ✅ Complete | — | [infrastructure](infrastructure/) |

### Phase 2 — Content Authoring (In Progress)

| Module | Version | Status | Tests | Docs |
|---|---|---|---|---|
| Question Bank | v1.0.0-pre | 🔧 Active | 53 tests | [question_bank.md](modules/question_bank.md) |
| Assessment | — | 📋 Planned | — | — |
| Career Profiling | — | 📋 Planned | — | — |
| Reporting | — | 📋 Planned | — | — |

### Phase 3 — Delivery & Services (Planned)

| Module | Version | Status |
|---|---|---|
| Training | — | 📋 Planned |
| Counseling | — | 📋 Planned |
| CMS | — | 📋 Planned |
| Notifications | — | 📋 Planned |

## Key Features Implemented

### Authentication & Authorization
- ✅ Email-based signup with email verification
- ✅ JWT auth (60-min access, 30-day refresh, rotation + blacklist)
- ✅ Proactive token refresh (refreshes 5 min before expiry)
- ✅ 11 system roles + custom roles with base_role inheritance
- ✅ Module-level RBAC (role × module × action)
- ✅ Bulk user upload (CSV)
- ✅ Role-specific profile fields per SRS

### Multi-Tenancy
- ✅ 3 organization types (corporate, corp_exclusive, channel_partner)
- ✅ Groups within organizations
- ✅ Organization members with admin toggle

### Question Bank
- ✅ 21 question types with type-specific editors
- ✅ 9 scoring modes with descriptions
- ✅ 3-stage review workflow (SME → Reviewer → Psychometrician)
- ✅ Category management (hierarchical tree + CRUD)
- ✅ Full-page question editor (create + edit)
- ✅ Media management (upload/URL/gallery modes, base64 data URLs)
- ✅ Flash item designer (text + image flash items)
- ✅ Hotspot area editor
- ✅ Question preview tab (candidate view)
- ✅ cj_admin override (edit/delete any question regardless of status)

### Infrastructure
- ✅ Django 5 + DRF + SimpleJWT backend
- ✅ React 18 + Vite + TypeScript + Tailwind frontend
- ✅ Caddy reverse proxy (auto-TLS, 120s timeouts)
- ✅ Docker (multi-stage builds)
- ✅ GitHub Actions CI (lint + test + coverage ≥80% + security)
- ✅ GitHub Actions CD (auto-deploy to GCP dev on push to main)
- ✅ Neon Postgres (dev DB)
- ✅ Vercel frontend CDN + Caddy reverse proxy

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + DRF 3.15 + SimpleJWT |
| Frontend | React 18 + Vite + TypeScript 5 + Tailwind CSS 3 |
| Database | PostgreSQL (Neon dev, OCI prod planned) |
| Reverse Proxy | Caddy (auto-TLS) |
| CI/CD | GitHub Actions |
| Container | Docker (multi-stage) |
| Deploy | GCP CE (dev) + OCI Ampere A1 (prod planned) |

## Deployment

- **Dev**: https://careerjudge.pp.ua (GCP CE, auto-deploys on push to main)
- **Prod**: Not yet deployed (OCI Ampere A1 planned, auto-deploy on tag v*.*.*)

## Next Priorities

1. **Assessment module** — sessions, 8 scoring modes implementation, fullscreen player
2. **Freeze question_bank v1.0.0** — after assessment module validates the question contract
3. **Career profiling** — assessment packages, profile generation
4. **Reporting** — PDF/HTML report generation
5. **Production deployment** — OCI Ampere A1 + CI/CD pipeline
