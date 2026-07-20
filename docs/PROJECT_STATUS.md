# Project Status — CareerJudge

> **Last updated**: 2026-07-20
> **Current phase**: Phase 3 (Career Profiling + Reporting — backend complete, frontend in progress)

## Completed Modules

### Phase 1 — Foundation (Complete)

| Module | Version | Status | Tests | Docs |
|---|---|---|---|---|
| Accounts | v1.1.0 | ✅ Frozen | 83 tests, 84% coverage | [accounts.md](modules/accounts.md) |
| Organizations | v1.0.0 | ✅ Frozen | 82% coverage | [organizations.md](modules/organizations.md) |
| Infrastructure | — | ✅ Complete | — | [infrastructure](infrastructure/) |
| Notifications | — | ✅ Active | Signal-based, bell icon, 8 event types | — |

### Phase 2 — Content Authoring (Complete)

| Module | Version | Status | Tests | Docs |
|---|---|---|---|---|
| Question Bank | v1.0.0 | ✅ Frozen | 96 tests (incl. psychometrics) | [question_bank.md](modules/question_bank.md) |
| Assessment | v1.0.0 | ✅ Frozen | 312 tests | [assessment.md](modules/assessment.md) |

### Phase 3 — Profiling & Reporting (Backend Complete)

| Module | Version | Status | Tests | Docs |
|---|---|---|---|---|
| Career Profiling | v1.0.0-pre | 🔧 Backend complete | 26 tests (engine + API) | — |
| Reporting | v1.0.0-pre | 🔧 Backend complete | 13 tests (group + HFMI/LFMI) | — |

### Phase 4 — Delivery & Services (Planned)

| Module | Version | Status |
|---|---|---|
| Training | — | 📋 Planned |
| Counseling | — | 📋 Planned |
| CMS | — | 📋 Planned |

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

### Assessment
- ✅ 6 models: Assessment, AssessmentSection (hierarchical L1–4), AssessmentQuestion, AssessmentSession, QuestionAttempt, SectionScore
- ✅ 9-mode scoring engine (BINARY, BINARY_FUZZY, PARTIAL, NEGATIVE, RANK, RANK_RATE, RATING, FORCED_CHOICE, FORCED_CHOICE_RATED)
- ✅ Exposure tracking + auto-deactivation at exposure_limit
- ✅ Per-section score aggregation with auto-computed percentages
- ✅ Attempt-rule enforcement (MULTIPLE_RETAKE, SINGLE_RETAKE, MULTIPLE_SESSION, SINGLE_SESSION)
- ✅ Session lifecycle: active → suspended (resumable) → completed
- ✅ Fullscreen delivery player with question palette, bookmark, timer
- ✅ Per-type answer inputs: MCQ, FITB, Rating, Rank, Forced-Choice, Hotspot (image click capture), Match (two-column pair matching), Grid (checkbox table)
- ✅ Flash simulation (respects SEQUENCE/RANDOM order, configurable interval & count, replayable)
- ✅ Passage display with optional display_duration countdown
- ✅ Results page with per-section score breakdown table
- ✅ Candidate isolation (users see only their own sessions)
- ✅ 76 backend tests (models, scoring, views)

### Career Profiling (Phase 3 — backend complete)
- ✅ ProfilingSolution, SelectedAssessment, BandDefinition, Band, MappingCriterion models
- ✅ MatchIndex computation engine implementing SRS §5.1-5.3 (3 modes):
  - Standard unranked: weight = criterion.weight (default 1.0)
  - Standard ranked (SRS §4.1.3): weight = RankValue looked up by rank_order
  - Polar (SRS §4.2): match_value from PolarMatchRule, weight from PolarRankValue by (match_code, rank_order)
- ✅ RankDefinition + RankValue models (Rank Order Chart per assessment)
- ✅ PolarMatchRule + PolarRankValue models (2D rank chart for polar assessments)
- ✅ Career metadata (stream, code, description) on MappingCriterion + denormalised on MatchIndex
- ✅ POST /api/career-profiling/solutions/<id>/compute/ endpoint (admin vs non-admin auth matrix)
- ✅ Idempotent computation (update_or_create on (solution, candidate, career_title, career_code))
- ✅ 26 backend tests (engine + API)

### Reporting (Phase 3 — backend complete)
- ✅ Report, ReportSection, ReportCutoff, ReportBand, TypologicalCode, PolarVariable, GeneratedReport models
- ✅ 4 report types: Descriptive, Typological, Interpretative, Group (SRS §3)
- ✅ 4 data input levels + 4 statistical conversions (Percentage, Percentile, STEN, STENINE)
- ✅ Polar variable computation (SRS §4: opposite = 100 - primary)
- ✅ Group report aggregation: candidate_count, avg/min/max, pass_rate, section_averages, distribution
- ✅ POST /api/reporting/reports/<id>/generate-group/ endpoint
- ✅ HFMI/LFMI data selection (SRS 06 §2.2): user-initiated (FMI range + manual selection) + system-initiated (top-N categories × top-N careers)
- ✅ POST /api/reporting/reports/<id>/select_data/ endpoint
- ✅ 13 backend tests (group report + HFMI/LFMI)

### Psychometric Analysis (Phase 3 — backend complete)
- ✅ Question model extended with IDI/TDI/BDI/DDI/item_total_correlation fields
- ✅ apps/question_bank/psychometrics.py implementing all 4 SRS 02 analyses:
  - Item Difficulty Index (MCQ): count-based (SRS §2)
  - Item Difficulty Index (non-MCQ): mean-based (SRS §3)
  - Item Discrimination Index (MCQ): (SRS §4)
  - Item Total Correlation Index (non-MCQ): (SRS §5)
- ✅ Top/bottom 27% group computation per SRS §2.2/§2.3
- ✅ Filter criteria: date range + assessment_id
- ✅ POST /api/question-bank/questions/psychometric-analysis/ endpoint
- ✅ Results persisted on Question model + psychometric_analyzed_at timestamp
- ✅ 14 backend tests covering MCQ + non-MCQ paths, edge cases (no variance, all correct, insufficient data)

### Infrastructure
- ✅ Django 5 + DRF + SimpleJWT backend
- ✅ React 18 + Vite + TypeScript + Tailwind frontend
- ✅ Caddy reverse proxy (auto-TLS, 120s timeouts)
- ✅ Docker (multi-stage builds)
- ✅ GitHub Actions CI (lint + test + coverage ≥80% + security)
- ✅ GitHub Actions CD (auto-deploy to dev server on push to main)
- ✅ Managed PostgreSQL (dev DB)
- ✅ Frontend CDN + Caddy reverse proxy

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + DRF 3.15 + SimpleJWT |
| Frontend | React 18 + Vite + TypeScript 5 + Tailwind CSS 3 |
| Database | PostgreSQL 16 (managed service for dev; self-hosted on prod VM) |
| Reverse Proxy | Caddy (auto-TLS) |
| CI/CD | GitHub Actions |
| Container | Docker (multi-stage) |
| Deploy | Cloud VM (dev) + Cloud VM (prod) — any standard provider |

## Deployment

- **Dev**: https://careerjudge.pp.ua (cloud VM, auto-deploys on push to main)
- **Prod**: Not yet deployed (cloud VM planned, auto-deploy on tag v*.*.*)

## Next Priorities

1. **Frontend UI for Phase 3 modules** — Career Profiling solution editor (rank chart, polar match rules), Reporting module (group report viewer, HFMI/LFMI selector, psychometric analysis dashboard)
2. **PDF generation** — currently reports are JSON via GeneratedReport.rendered_data; add WeasyPrint-based PDF rendering for downloadable reports
3. **Report Layout drag-drop editor** (SRS §3_layout) — ReportSection has order field but no drag-drop UI
4. **Production deployment** — provision prod cloud VM + CI/CD pipeline
5. **End-to-end staging validation** — exercise all 21 question types through the assessment player
6. **Phase 4 modules** — Training, Counseling, CMS
