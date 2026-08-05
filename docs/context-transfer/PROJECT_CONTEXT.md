# CareerJudge — Context Transfer Brief

> **Purpose:** This file gives a new AI agent (e.g., Z.ai Code) the full
> project context to continue development without any information loss.
> Last updated: 30 July 2026.

## Quick Start for New Agent

1. Read this file (PROJECT_CONTEXT.md) for a high-level overview
2. Read WORKLOG.md for the complete development history (every task, decision, commit)
3. Read REVIEW_TRACKING.md (in docs/review-docs/) for all client review docs + resolution status
4. Read the spec files in `specs/` for SRS requirements
5. Read the review PDFs in `docs/review-docs/` for client feedback
6. Clone the repo, run `cd backend && source .venv/bin/activate && python manage.py runserver`
7. Frontend: `cd frontend && npm ci && npm run dev`

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + DRF 3.15 + SimpleJWT |
| Frontend | React 18 + Vite + TypeScript 5 + Tailwind CSS 3 + TanStack Query |
| Database | PostgreSQL 16 (dev: managed service, prod: self-hosted) |
| Reverse Proxy | Caddy (auto-TLS) |
| CI/CD | GitHub Actions (lint + test + deploy on push to main) |
| Container | Docker (multi-stage builds) |
| PDF | WeasyPrint |
| Deploy | https://careerjudge.pp.ua (dev server, auto-deploys on push to main) |

## Repo

https://github.com/sanjayaluva/careerjudge_python

## Modules — All Complete

| # | Module | Status | Tests | Key Features |
|---|---|---|---|---|
| 1 | Accounts | ✅ Frozen | 83 tests, 84% coverage | Email auth, JWT, 11 roles, RBAC, bulk upload |
| 2 | Organizations | ✅ Frozen | 82% coverage | Multi-tenancy, corporate/channel-partner |
| 3 | Question Bank | ✅ Frozen | 96 tests | 21 question types, 9 scoring modes, rich-text editor, review workflow |
| 4 | Assessment | ✅ Active | 117 tests | Session player, 9-mode scoring, sub-question pooling, anti-cheating player |
| 5 | Career Profiling | ✅ Complete | 26 tests | Match index computation, rank charts, polar rules |
| 6 | Reporting | ✅ Complete | 22 tests | 4 report types, PDF generation, layout editor |
| 7 | Psychometric Analysis | ✅ Complete | 14 tests | IDI/TDI/BDI/DDI + item-total correlation |
| 8 | Training | ✅ Complete | 32 tests | Courses, lessons, live sessions, Zoom, progress tracking |
| 9 | Counseling | ✅ Complete | 21 tests | Booking, counsellor profiles, cancellations, follow-ups |
| 10 | CMS | ✅ Complete | — | Pages, banners, WYSIWYG editor, public homepage |
| 11 | Payments | ✅ Complete | — | Stripe + Razorpay |
| 12 | Tasks | ✅ Complete | 24 tests | SRS 09 admin task management |
| 13 | Notifications | ✅ Active | — | In-app bell icon, signal-based, 8 event types |

**Total: 496 backend tests (80% coverage) + 30 frontend tests — all passing**

## Key Recent Work (Last 30+ Commits)

### Multi-sub-question pooling (major feature)
- Questions with shared media (audio/video/passage/image) and N sub-questions
- Each sub-question has its own text + options + independent scoring (0 or 1)
- Parent question is a wrapper — no score of its own
- In-question sub-question navigation (Next/Previous cycles through sub-questions)
- Layout: Text 1 → Media (Show Content button) → Text 2 → SubQ Text → Options
- Navigation locked during content presentation
- Per-sub-question text field (`sub_question_texts` JSON list on Question model)

### Anti-cheating audio/video player
- "Click to Play" button instead of native controls (for not_permitted mode)
- No download (controlsList="nodownload" + context menu disabled)
- No seeking/rewinding (onSeeking intercepts backward seeks)
- Play once — after playback ends, player disappears, onPresentationEnd fires
- On revisit (Previous button), player is locked entirely

### Rich-text editor
- WysiwygEditorLite component (TipTap-based) wired into all question editors
- Renders as HTML in player, detail page, previews via RichText component
- stripHtml() helper for list/table snippets

### System Testing & Review Feedback Report (67 items — all done)
- Multi-answer scoring (+1/-1, min 0)
- Display mode (timed/unlimited) + replay mode (permitted/not_permitted)
- Option layout (1/2/3 columns)
- Hotspot visibility (transparent/visible)
- Passage "Click to Show" button + timer starts on click
- Image Display "Click to Show" button + timer
- Flash player polish (bigger play button, hidden specs, no replay, key prop fix)
- Grid numbered-button UI with cell popups
- Match dummy options + Group B shuffle
- FITB flash any-order scoring
- Hotspot click-accuracy tolerance (all 3 shape types)
- Assessment summary counts (Total/Answered/Remaining/Bookmarked)
- Submit loading overlay

### Multiple Questions Display Style document
- Two-phase display: media phase → sub-question phase
- Media only on sub-question 0; sub-questions 2+ show only SubQ Text + Options
- Sub-questions delivered in order 1, 2, 3 (no random)

## Database Migrations

Run `python manage.py migrate` after cloning. Key recent migrations:
- 0010_feedback_report_fields (display_mode, replay_mode, option_layout, hotspot_visibility)
- 0011_question_sub_question_count_and_more (sub_question_count, sub_question_text_2_list)
- 0012_question_sub_question_texts_and_more (sub_question_texts)

## Environment Setup

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Create .env with:
# DJANGO_SETTINGS_MODULE=config.settings.dev
# SECRET_KEY=dev-secret-key-not-for-prod-12345678901234567890
# DEBUG=true
# ALLOWED_HOSTS=localhost,127.0.0.1
# CORS_ALLOWED_ORIGINS=http://localhost:5173
# DATABASE_URL= (leave empty for SQLite)
python manage.py migrate
python manage.py seed_demo  # creates 10 roles + 10 users + superuser
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm ci  # uses .npmrc with legacy-peer-deps=true
npm run dev
```

### Seed Demo Credentials
- Admin: admin@demo.careerjudge.pp.ua / Demo@1234
- SME: sme@demo.careerjudge.pp.ua / Demo@1234
- Reviewer: reviewer@demo.careerjudge.pp.ua / Demo@1234
- (see seed_demo.py for all 10 users)

## Pending Work

1. **2 new review docs** (psychometric questions + course/counselling) — not yet provided by client
2. **Full end-to-end regression testing** of all question types in a live session
3. **Production deployment** — provision prod cloud VM + CI/CD pipeline
4. **Edge case testing** — hotspot click accuracy on production-sized images, flash timing on slower devices

## Key Files to Read

| File | Purpose |
|---|---|
| `docs/context-transfer/WORKLOG.md` | Complete development history (every task, decision, commit) |
| `docs/review-docs/REVIEW_TRACKING.md` | All client review docs + their resolution status |
| `docs/review-docs/CareerJudge_Feedback_Status_Response.pdf` | 67-item implementation status report |
| `specs/11_SRS.json` | Full SRS with 46 use cases |
| `specs/` (all JSON files) | Module-by-module specs (question types, scoring, training, counseling, etc.) |
| `docs/PROJECT_STATUS.md` | Module status overview (may be slightly outdated) |
| `docs/GAP_ANALYSIS.md` | Original gap analysis (historical reference) |
