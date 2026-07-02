# Phase 2 Plan — Question Bank + Assessment + Organizations

> Started: 2026-07-01
> Prerequisite: Phase 1 (accounts) frozen at v1.0.0

## Overview

Phase 2 builds the core assessment engine — the heart of CareerJudge. It covers:
1. **Question Bank** — author, review, and manage 21 question types
2. **Assessment** — configure tests, take assessments, score with 8 scoring modes
3. **Organizations** — link users to corporate entities (multi-tenancy foundation)

## SRS Use Cases Covered

### Question Bank (UC010-UC017, UC025-UC026)

| UC# | Title | Actor | Module |
|---|---|---|---|
| UC010 | Add Category/Sub-category | Psychometrician | question_bank |
| UC011 | Request to Delete Category/Sub-category | Psychometrician | question_bank |
| UC012 | Delete Category/Sub-category | CJ Admin | question_bank |
| UC013 | Add Questions | SME | question_bank |
| UC014 | Review Questions | Reviewer | question_bank |
| UC015 | Confirm Questions | Psychometrician | question_bank |
| UC016 | Request to Delete Question | Psychometrician | question_bank |
| UC017 | Delete Question | CJ Admin | question_bank |
| UC025 | Filter Data | Psychometrician | question_bank |
| UC026 | Set Psychometric values | System | question_bank |

### Assessment (UC029-UC030)

| UC# | Title | Actor | Module |
|---|---|---|---|
| UC029 | Prepare Assessment Blueprint | Psychometrician | assessment |
| UC030 | Take assessment | Individual/Corporate users | assessment |

### Organizations (multi-tenancy)

No explicit use cases in SRS, but roles imply:
- Corporate Admin manages corporate users
- Corporate Exclusive manages exclusive corporate users
- Group Admin manages groups within a corporate
- Channel Partner manages their own users

## Module 1: organizations (1-2 weeks)

### Models
- `Organization` — corporate entity (name, type: corporate/corp_exclusive/channel_partner, status)
- `Group` — sub-group within an organization
- `OrganizationMember` — links User to Organization with a role

### APIs
- CRUD for organizations (cj_admin, corp_admin)
- CRUD for groups within an organization (corp_admin, group_admin)
- Link users to organizations (corp_admin)
- List users within an organization/group

### Frontend
- Organizations list page (table with search, filter by type)
- Organization detail page (shows members, groups)
- Create/edit organization modal
- Group management within organization

## Module 2: question_bank (2-3 weeks)

### Models (per `00_django_model_hints.json` + `00_question_types_spec.json`)

- `Category` — question categories/sub-categories (UC010)
- `Test` — assessment test definition
- `Section` — sections within a test
- `Question` — supports 21 question types:
  - MCQ variants: text/image, audio, video, flash, passage, image display
  - FITB variants: single, multi-field, flash, image flash
  - Match Following, Grid List Selection
  - Hotspot (single, multi)
  - Rank (simple, then rate)
  - Standard Rating Scale
  - Forced Choice (single level, two level)
- `ResponseOption` — answer options for MCQ/FITB/Match/Grid/Rank/Forced-Choice
- `MediaFile` — audio/video for question types 1c/1d
- `FlashItem` — items for flash question types 1e/1f/2c/2d
- `HotspotArea` — clickable areas for hotspot questions
- `CorrectAnswer` — correct answers (up to 5 per FITB, etc.)
- `QuestionReview` — review workflow (SME creates → Reviewer reviews → Psychometrician confirms)

### APIs
- Category CRUD (UC010, UC011, UC012)
- Question CRUD with all 21 types (UC013, UC016, UC017)
- Question review workflow (UC014, UC015):
  - POST `/api/question-bank/questions/<id>/submit-for-review/` (SME)
  - POST `/api/question-bank/questions/<id>/review/` (Reviewer — approve/reject)
  - POST `/api/question-bank/questions/<id>/confirm/` (Psychometrician)
- Question filtering (UC025) — by category, type, status, difficulty
- Psychometric values (UC026) — set difficulty, discrimination index, etc.

### Frontend
- Question Bank dashboard (stats: total questions, by type, by status)
- Category management (tree view with add/delete request)
- Question list (filterable by category, type, status, difficulty)
- Question editor (dynamic form based on question type — 21 variants)
- Question review queue (for reviewers)
- Question confirmation queue (for psychometricians)

## Module 3: assessment (2-3 weeks)

### Models (per `03_assessment_configuration.json` + `00_scoring_rules.json`)

- `AssessmentBlueprint` — test configuration (UC029):
  - Selected sections/questions
  - Total duration, display order (random/static)
  - Scoring configuration
- `TestSession` — candidate's assessment session:
  - User, assessment, start/end time, status (not_started/in_progress/suspended/completed)
  - Remaining time, completion percentage
- `QuestionAttempt` — candidate's answer to a question:
  - Session, question, raw_answer (JSON), score, scored_at
  - Supports all 21 question types via JSONField

### Scoring (8 modes per `00_scoring_rules.json`)
1. BINARY — correct/incorrect (0 or 1)
2. BINARY_FUZZY — FITB with fuzzy/percentage match
3. PARTIAL — partial credit for multi-answer
4. NEGATIVE — negative marking for wrong answers
5. RANK — scoring for ranking questions
6. RANK_RATE — rank then rate
7. RATING — rating scale scoring
8. FORCED_CHOICE — forced choice scoring

### APIs
- Assessment blueprint CRUD (UC029)
- Session management:
  - POST `/api/assessment/sessions/` — create session
  - GET `/api/assessment/sessions/<id>/` — resume session
  - PATCH `/api/assessment/sessions/<id>/` — suspend/complete
- Question attempts:
  - POST `/api/assessment/sessions/<id>/attempts/` — submit answer
  - Scoring happens server-side based on question's scoring_type
- Results:
  - GET `/api/assessment/sessions/<id>/results/` — scored results

### Frontend
- Assessment configuration page (psychometrician)
- Assessment list (admin/corp_admin — assign to users)
- Candidate assessment player (SPA with timer, auto-save, suspend/resume):
  - Renders all 21 question types
  - Client-side timing for flash questions (ms-precision)
  - Hotspot click capture
  - Audio/video playback
  - Auto-save answers
  - Suspend/resume support
- Assessment results page (per session)

## Implementation Order

1. **organizations** (1-2 weeks) — foundation for multi-tenancy
2. **question_bank** (2-3 weeks) — questions must exist before assessments
3. **assessment** (2-3 weeks) — depends on question_bank

Total Phase 2 estimate: 5-8 weeks

## Branch Strategy

```
main (v1.0.0 frozen)
  └─ develop
       └─ feature/organizations-models
       └─ feature/organizations-api
       └─ feature/organizations-frontend
       └─ feature/question-bank-models
       └─ feature/question-bank-api
       └─ feature/question-bank-frontend
       └─ feature/assessment-models
       └─ feature/assessment-api
       └─ feature/assessment-frontend
```

Each feature branch → PR → review → merge to develop → test → merge to main → tag.

## Questions for client

Before starting Phase 2, I need clarification on:

1. **Organizations**: The SRS doesn't have explicit organization management use cases. Should I infer the model from the roles (Corporate Admin, Corporate Exclusive, Channel Partner, Group Admin)? Or is there a separate spec for this?

2. **Question types priority**: All 21 types at once, or should I phase them? E.g.:
   - Phase 2a: MCQ text/image, FITB single, Rating, Match (most common)
   - Phase 2b: Audio, video, flash, hotspot, rank, forced-choice (complex)

3. **Assessment player**: Should the candidate player be a separate route/SPA (for fullscreen, no sidebar) or within the dashboard shell?

4. **Psychometric values (UC026)**: What psychometric properties should be stored per question? (difficulty index, discrimination index, etc.) — the spec mentions it but doesn't define the fields.
