# Assessment Module — v1.0.0 (Active development, not yet frozen)

> **Version**: v1.0.0 (pre-freeze)
> **Phase**: 2 (in progress)
> **Test coverage**: 76 tests (models, scoring, views); 87% backend coverage overall
> **Frozen**: No — will freeze at v1.0.0 after end-to-end candidate delivery is validated in staging

## Overview

The assessment module is the candidate-facing delivery engine for CareerJudge. It takes a published Assessment definition (with its hierarchical sections and assigned questions from the Question Bank), spawns per-candidate sessions, captures answers as flexible JSON, and runs them through a 9-mode scoring engine to produce total + per-section scores.

The module wires together the authored content (Question Bank) and the eventual reporting/profiling layer (Phase 3) — every confirmed question gets an `exposure_count` bump when used in a session, and questions auto-deactivate when their `exposure_limit` is reached.

## Version History

### v1.0.0-pre (2026-07-11) — Active development

**Core features:**

- 6 models: `Assessment`, `AssessmentSection` (hierarchical L1–4), `AssessmentQuestion` (links to Question Bank), `AssessmentSession`, `QuestionAttempt`, `SectionScore`
- 4 ViewSets: `AssessmentViewSet` (CRUD + publish + start/submit session), `AssessmentSectionViewSet`, `AssessmentQuestionViewSet`, `SessionViewSet` (candidate-facing)
- 9-mode scoring engine (`scoring.py`) covering every SRS-defined scoring type:
  - `BINARY` — exact-match 0/1 (MCQ, FITB single, Hotspot single)
  - `BINARY_FUZZY` — list or percentage match (FITB single)
  - `PARTIAL` — +1 per correct item (FITB multi-field, Match-the-following)
  - `NEGATIVE` — +1 correct, −0.25 wrong (Hotspot multi, configurable for MCQ)
  - `RANK` — count of correctly-ordered pairs (Rank Simple)
  - `RANK_RATE` — rank_score × rating_score (Rank-then-Rate)
  - `RATING` — rating point = score, forward or reverse (Standard Rating Scale)
  - `FORCED_CHOICE` — selected option's predefined_score (Forced-Choice Single Level)
  - `FORCED_CHOICE_RATED` — predefined_score × rating (Forced-Choice Two-Level)
- Exposure tracking: every scored attempt increments `Question.exposure_count`; auto-deactivation at `exposure_limit`
- Per-section aggregation: `SectionScore` records are created/updated on session submit, with auto-computed `percentage`
- Attempt-rule enforcement: `MULTIPLE_RETAKE`, `SINGLE_RETAKE`, `MULTIPLE_SESSION`, `SINGLE_SESSION`
- Session lifecycle: `active` → `suspended` (resumable) → `completed`; resuming a suspended session reactivates it
- Pre-created `QuestionAttempt` records when a session starts — the candidate-facing player can render the question palette immediately

**Frontend pages:**

- `AssessmentsPage` — list with search, status filter, create modal, publish/delete actions
- `AssessmentDetailPage` — 4 tabs:
  - Overview (config + publish/start-session buttons)
  - Sections (hierarchical tree with CRUD, parent/child levels 1–4)
  - Questions (assign question-bank questions to a section via the question browser)
  - Sessions (start a session as the current candidate)
- `SessionPlayerPage` — fullscreen delivery player:
  - Top bar with title, question index, answered/bookmarked counts, live countdown timer, Suspend + Submit buttons
  - Question palette (numbered grid with answered/bookmarked/unanswered state)
  - Per-type `AnswerInput` rendering for: MCQ (radio/checkbox), FITB (text inputs), Rating (numbered circles), Rank (click-to-rank), Forced-Choice (radio + optional rating), Hotspot (image click capture with proportional coordinate scaling), Match (two-column pair matching), Grid (checkbox table)
  - `FlashSimulation` — plays flash items one at a time at the configured interval, respects `flash_order` (SEQUENCE/RANDOM), candidate can replay
  - `PassageDisplay` — collapsible passage panel with optional `display_duration_seconds` countdown
  - Auto-submit on timer expiry
  - Bookmark + skip + previous/next navigation
- `SessionResultsPage` — score summary (total, percentage, pass/fail), per-section breakdown table, session metadata

**Bug fixes applied during development:**

- Missing migrations: `assessment.0001_initial` was not generated — caused `no such table: assessment_assessment` and broke the entire CI test suite (171 errors). Migrations now committed.
- URL doubling: `path("api/assessments/", include(...))` + `router.register("assessments", ...)` produced `/api/assessments/assessments/`. Fixed by changing the outer prefix to `api/` so the router owns the `assessments/` namespace.
- `QuestionAttemptSerializer` was using `QuestionListSerializer` for `question_detail`, which omits options/flash_items/hotspot_areas/passage — the player couldn't render anything. Switched to `QuestionDetailSerializer`.
- `AssessmentSessionSerializer` didn't expose `total_duration_seconds`, so the player couldn't initialise the timer. Added as a read-only computed field sourced from `assessment.total_duration_seconds`.
- `updated_at` field didn't exist on `AssessmentSession` — calls to `save(update_fields=[..., "updated_at"])` raised 500. Removed the non-existent field from `update_fields` everywhere.
- `start_session` applied `SINGLE_SESSION` / `SINGLE_RETAKE` restrictions before checking for a resumable session, so candidates with an active session got a 403 instead of a resume. Reordered: resume check first, attempt-rule restrictions only apply when creating a NEW session.
- `AssessmentSectionSerializer` and `AssessmentQuestionSerializer` had `assessment` / `section` as writable required fields, but the ViewSets set them in `perform_create` — POSTs returned 400. Made the FK fields read-only.
- `_score_partial` returned `max_score = len(options)` for Match questions (counts both A and B sides), so a 3-pair match had max=6 instead of 3. Fixed to detect match-type options and halve the count.
- `_score_rank` and `_get_max_score` used `n*(n+1)/2` for max_score (sum of 1..n), but the actual scoring counts pairs `n*(n-1)/2`. Aligned both formulas.
- `timezone` import was at the bottom of `views.py` (E402) — moved to the top with the other Django imports.
- Module omitted from coverage config (`apps/assessment/*` was in the omit list) — removed so the new tests count toward the 80% gate.

## Public API

Base URL: `/api/assessments/`

### Assessments (admin/author)

| Method | Path | Description | Permission |
|---|---|---|---|
| GET | `/api/assessments/` | List assessments (filters: `search`, `status`) | `assessment.view` |
| POST | `/api/assessments/` | Create assessment | `assessment.add` |
| GET | `/api/assessments/<id>/` | Retrieve assessment (with nested sections tree) | `assessment.view` |
| PATCH | `/api/assessments/<id>/` | Update assessment (draft only) | `assessment.change` |
| DELETE | `/api/assessments/<id>/` | Delete assessment (draft only) | `assessment.delete` |
| POST | `/api/assessments/<id>/publish/` | Publish assessment (draft → published) | `assessment.change` |
| GET | `/api/assessments/<id>/sessions/` | List all sessions for this assessment | `assessment.view` |
| POST | `/api/assessments/<id>/start_session/` | Start or resume a candidate session | `assessment.view` |

### Sections (nested under assessment)

| Method | Path | Description |
|---|---|---|
| GET | `/api/assessments/<aid>/sections/` | List sections (flat; subsections are nested in the response) |
| POST | `/api/assessments/<aid>/sections/` | Create section (level 1–4, optional parent) |
| PATCH | `/api/assessments/<aid>/sections/<id>/` | Update section |
| DELETE | `/api/assessments/<aid>/sections/<id>/` | Delete section (cascades to subsections + assigned questions) |

### Question Assignment (nested under section)

| Method | Path | Description |
|---|---|---|
| GET | `/api/assessments/<aid>/sections/<sid>/questions/` | List questions assigned to the section |
| POST | `/api/assessments/<aid>/sections/<sid>/questions/` | Assign a question-bank question to the section |
| DELETE | `/api/assessments/<aid>/sections/<sid>/questions/<id>/` | Remove a question from the section |

### Sessions (candidate-facing)

| Method | Path | Description |
|---|---|---|
| GET | `/api/assessments/sessions/` | List the current user's sessions |
| GET | `/api/assessments/sessions/<id>/` | Retrieve session (includes `total_duration_seconds` for the player timer) |
| GET | `/api/assessments/sessions/<id>/questions/` | Get all questions for the session (with full `question_detail` including options, flash items, hotspot areas, etc.) |
| POST | `/api/assessments/sessions/<id>/answer/` | Save answer for one question (or mark bookmarked/skipped) |
| POST | `/api/assessments/sessions/<id>/submit/` | Submit entire session — calculates scores and returns `session` + `section_scores` |
| POST | `/api/assessments/sessions/<id>/suspend/` | Suspend session (can be resumed via `start_session`) |
| GET | `/api/assessments/sessions/<id>/section_scores/` | Fetch per-section score breakdown (after submit) |

### Example: Submit Answer Payload

```json
{
  "question_id": 42,
  "sub_question_index": 0,
  "raw_answer": {
    "selected_option_ids": [103, 105]
  }
}
```

The `raw_answer` schema is flexible (JSONField) and varies by question type — see the `QuestionAttempt.raw_answer` docstring for the full matrix.

### Example: Submit Session Response

```json
{
  "message": "Session submitted successfully.",
  "data": {
    "session": {
      "id": 17,
      "assessment": 3,
      "assessment_title": "Aptitude Battery",
      "candidate": 5,
      "candidate_name": "Jane Doe",
      "status": "completed",
      "started_at": "2026-07-11T10:00:00Z",
      "completed_at": "2026-07-11T11:15:00Z",
      "total_score": 6.0,
      "max_score": 6.0,
      "percentage": 100.0,
      "total_duration_seconds": 3600
    },
    "section_scores": [
      {
        "id": 1,
        "session": 17,
        "section": 5,
        "section_title": "Quantitative",
        "raw_score": 4.0,
        "max_score": 4.0,
        "percentage": 100.0
      },
      {
        "id": 2,
        "session": 17,
        "section": 6,
        "section_title": "Verbal",
        "raw_score": 2.0,
        "max_score": 2.0,
        "percentage": 100.0
      }
    ]
  }
}
```

## Data Model

### Assessment

Top-level test definition. Created by `cj_admin`, `corp_admin`, or `psychometrician`.

- `title` (required), `objective`, `description`, `instructions`
- `status`: `draft` → `published` → `archived`
- `total_duration_seconds` (nullable — NULL = no time limit)
- `timer_level`: `assessment` | `level1` | `level2` | `level3` | `level4` | `question`
- `display_order`: `STATIC` | `RANDOM`
- `navigation_rule`: `FREE` | `PREV_SECTION` | `NO_BACKWARD_SECTION` | `NO_BACKWARD_QUESTION`
- `attempt_rule`: `MULTIPLE_RETAKE` | `SINGLE_RETAKE` | `MULTIPLE_SESSION` | `SINGLE_SESSION`
- `created_by` FK → `User`

### AssessmentSection

Hierarchical variable structure within an assessment (up to 4 levels of nesting via `parent` FK).

- `assessment` FK → `Assessment`
- `parent` FK → `self` (nullable; NULL = top-level L1)
- `title`, `description`
- `level` (1–4), `order`
- `duration_seconds` (only used if `assessment.timer_level` matches this level)

### AssessmentQuestion

Links a question from the Question Bank to a section.

- `section` FK → `AssessmentSection`
- `question` FK → `question_bank.Question`
- `order`, `sub_question_index` (for multi-sub-question types 1c–1h)
- `score_override` (nullable — if NULL, uses question's default max score)
- `duration_seconds` (per-question timer, only if `timer_level='question'`)
- Unique constraint: `(section, question, sub_question_index)`

### AssessmentSession

A candidate's attempt at an assessment.

- `assessment` FK, `candidate` FK → `User`
- `status`: `active` | `suspended` | `completed` | `abandoned`
- `started_at` (auto), `suspended_at`, `resumed_at`, `completed_at`
- `total_score`, `max_score`, `percentage` (null until scored)

### QuestionAttempt

One candidate's answer to one question within a session.

- `session` FK, `question` FK, `section` FK (nullable)
- `sub_question_index`
- `status`: `not_attempted` | `attempted` | `bookmarked` | `skipped`
- `raw_answer` JSONField — flexible schema per question type:
  - MCQ: `{"selected_option_ids": [1, 3]}`
  - FITB: `{"answers": ["Paris", "France"]}`
  - Match: `{"pairs": [{"a_id": 1, "b_id": 3}, ...]}`
  - Grid: `{"selected_cells": [{"r": 0, "c": 1}, ...]}`
  - Hotspot: `{"clicks": [{"x": 150, "y": 200}]}`
  - Rank: `{"ranking": [3, 1, 4, 2]}`
  - Rating: `{"rating": 4}`
  - Forced Choice: `{"selected_option_id": 2, "rating": 5}`
- `score`, `max_score` (set on submit by `calculate_session_scores`)
- `answered_at`, `time_spent_seconds`
- Unique constraint: `(session, question, sub_question_index)`

### SectionScore

Aggregated score per section per session. Feeds the reporting/profiling layer.

- `session` FK, `section` FK
- `raw_score`, `max_score`, `percentage` (auto-computed in `save()`)
- Unique constraint: `(session, section)`

## Scoring Engine

Located in `apps/assessment/scoring.py`. Two public entry points:

- `score_question(question, raw_answer) → (score, max_score)` — scores a single attempt
- `calculate_session_scores(session) → session` — iterates all attempts, scores each, aggregates `SectionScore` records, updates session totals, increments `exposure_count` on each question, auto-deactivates questions at `exposure_limit`

The 9 scorers are registered in `SCORERS` dict keyed by `Question.scoring_type`. Unknown scoring types fall back to `_score_binary`.

### Max-Score Formulas

| Scoring Type | Max Score |
|---|---|
| BINARY / BINARY_FUZZY / NEGATIVE | 1.0 |
| PARTIAL (FITB) | number of fields (options) |
| PARTIAL (Match) | number of pairs = options / 2 |
| RANK | n×(n−1)/2 (number of unique pairs) |
| RANK_RATE | n × max_rating |
| RATING | rating_scale_points |
| FORCED_CHOICE | max(predefined_score) |
| FORCED_CHOICE_RATED | max(predefined_score) × max_rating |

## Permissions

Permission class: `HasAssessmentPermission` (extends `HasModulePermission`).

| Action | Required permission |
|---|---|
| list, retrieve, start_session, submit_session | `assessment.view` |
| create | `assessment.add` |
| update, partial_update, publish | `assessment.change` |
| destroy | `assessment.delete` |

The candidate-facing `SessionViewSet` only requires `IsAuthenticated` — candidates always see their own sessions. The `get_queryset` filter ensures they cannot retrieve other users' sessions (returns 404).

## Frontend Integration

### API Client (`frontend/src/api/assessment.ts`)

Typed functions for every endpoint, plus TypeScript interfaces for `Assessment`, `AssessmentSection`, `AssessmentSession`, `AssessmentQuestion`, `SessionQuestion` (with nested `question_detail`), and `SectionScore`.

### Player Timer

The `AssessmentSessionSerializer` exposes `total_duration_seconds` (sourced from the assessment) so the player can initialise a countdown without an extra API call. The player computes remaining time from `started_at` to handle page refreshes mid-session. Server-side enforcement is the source of truth; the client-side timer is purely UX.

### Flash & Passage Delivery

The `SessionPlayerPage` includes dedicated components for stimulus-first question types:

- **`FlashSimulation`**: plays flash items one at a time at `flash_interval_ms`. Respects `flash_order` (SEQUENCE = saved order, RANDOM = Fisher-Yates shuffle). Honours `flash_display_count` (subset of items). Candidate can replay on demand.
- **`PassageDisplay`**: shows passage title + body with an optional `display_duration_seconds` countdown. When time elapses, the passage collapses (simulates exam conditions) but the candidate can manually re-show it.

## Testing

- **76 tests** in `apps/assessment/tests/`:
  - `test_models.py` — model defaults, hierarchy, unique constraints, percentage auto-calc
  - `test_scoring.py` — all 9 scoring modes, max-score formulas, end-to-end `calculate_session_scores` with exposure tracking and auto-deactivation
  - `test_views.py` — assessment CRUD, publish flow, section CRUD, question assignment, full session flow (start → answer → submit → scores), suspend/resume, candidate isolation
- Backend coverage with assessment included: **87.18%** (well above the 80% CI gate)

## Known Limitations / Future Work

- **Timer enforcement is client-side only.** A determined candidate can disable the JS timer. Server-side enforcement (rejecting answers submitted after `started_at + total_duration_seconds`) is a Phase 3 hardening task.
- **No `abandoned` transition.** Sessions can be `active`/`suspended`/`completed`, but `abandoned` is in the model choices with no transition path yet. Add a celery beat task to auto-abandon stale active sessions.
- **No question-level timer in the player.** `AssessmentQuestion.duration_seconds` is stored but the player only shows the assessment-level timer. Add per-question countdown when `timer_level='question'`.
- **No section-level timer.** Same gap for `timer_level='level1'..'level4'`.
- **`score_override` is not yet applied.** The scoring engine uses the question's default max score; the per-assignment override is stored but ignored.
- **No retake history view.** Candidates can take an assessment multiple times (if `MULTIPLE_RETAKE`), but there's no UI to compare past attempts.
- **No proctoring.** No tab-switch detection, no copy/paste blocking, no webcam snapshots — these are Phase 3+ features per SRS.
