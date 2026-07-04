# Question Bank Module — v1.0.0 (Active development, not yet frozen)

> **Version**: v1.0.0 (pre-freeze)
> **Phase**: 2 (in progress)
> **Test coverage**: 53 tests
> **Frozen**: No — will freeze at v1.0.0 after assessment module validates the question contract

## Overview

The question bank module is the core content authoring system. It supports 21 question types, 9 scoring modes, a 3-stage review workflow (SME → Reviewer → Psychometrician), and full media management (images, audio, video, flash items, hotspot areas).

## Version History

### v1.0.0-pre (2026-07-04) — Active development

**Core features:**
- 21 question types with type-specific editors (MCQ 8 variants, FITB 4 variants, Match, Grid, Hotspot 2 variants, Rank 2 variants, Rating, Forced-Choice 2 variants)
- 9 scoring modes with in-editor descriptions (BINARY, BINARY_FUZZY, PARTIAL, NEGATIVE, RANK, RANK_RATE, RATING, FORCED_CHOICE, FORCED_CHOICE_RATED)
- 3-stage review workflow: draft → pending_content_review → content_reviewed → pending_psychometric_review → confirmed
- Send back / reject actions with reviewer comments (visible in Reviews tab)
- Category management: hierarchical tree, CRUD, filter questions by category
- Full-page question editor (create + edit) with type-specific sub-editors
- cj_admin override: can edit/delete any question regardless of status

**Media management:**
- MediaManager component with 3 modes: upload (base64), URL, gallery (previously uploaded)
- Images/audio/video stored as base64 data URLs or external URLs in TextField columns
- No file storage infrastructure needed — simplifies deployment
- FlashItemsEditor: add/edit/delete text + image flash items with timing settings (interval ms, display count)
- HotspotArea editor: pixel-defined click zones for hotspot questions

**Frontend pages:**
- QuestionBankPage: full-width list with filters (search, type, status, mine, category), pagination, edit/delete/submit actions
- QuestionDetailPage: 5 tabs (Details, Options, Media, Reviews, Preview) with candidate preview by question type
- QuestionEditorPage: full-page editor (replaces modal) with type-specific sub-editors + flash items preview
- CategoryManager: collapsible tree + CRUD, embedded via modal on QuestionBankPage

**Performance optimizations:**
- Bulk options save: single API call syncs create+update+delete in one request, wrapped in transaction.atomic()
- Parallel API calls: media/hotspot/flash item deletes and creates use Promise.all
- Combined 4 separate bulkSaveOptions calls into 1 (regular options + match pairs + grid cells + rating labels)
- Caddy reverse_proxy timeouts: 120s for large base64 payloads
- Axios timeout: 120s (matches Caddy)

**Bug fixes applied:**
- ImageField → TextField migration: base64 data URLs rejected by DRF ImageField (4 migrations total)
- None → empty string normalization in serializers: prevents IntegrityError on null image_file
- Bulk options kept_ids tracking: newly-created options were immediately deleted (fixed)
- CategoryTreeSerializer: added description field (was missing, broke edit modal)
- Option type labels: show TEXT/IMAGE/TEXT & IMAGE based on content (not always TEXT)
- Preview placeholders removed: no "(option 1)" text for empty options

## Public API

### Question endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/question-bank/questions/` | List questions (filters: category, type, status, difficulty, mine) |
| POST | `/api/question-bank/questions/` | Create question (SME, psychometrician, cj_admin) |
| GET | `/api/question-bank/questions/:id/` | Retrieve question detail (with nested options, media, flash, hotspots, reviews) |
| PATCH | `/api/question-bank/questions/:id/` | Update question (cj_admin can edit any; others only draft/sent_back) |
| DELETE | `/api/question-bank/questions/:id/` | Delete question (cj_admin can delete any; others only draft/sent_back) |
| POST | `/api/question-bank/questions/:id/submit-for-review/` | SME submits for content review |

### Review endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/question-bank/questions/:id/review/` | Submit review action (approve/send_back/reject) |
| GET | `/api/question-bank/questions/:id/reviews/` | List review history |

### Category endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/question-bank/categories/` | List categories (filter by parent) |
| POST | `/api/question-bank/categories/` | Create category (psychometrician, cj_admin) |
| GET | `/api/question-bank/categories/:id/` | Retrieve category |
| PATCH | `/api/question-bank/categories/:id/` | Update category |
| DELETE | `/api/question-bank/categories/:id/` | Delete category |
| GET | `/api/question-bank/categories/tree/` | Get hierarchical tree view |

### Child resource endpoints (nested under question)

| Method | Path | Description |
|---|---|---|
| POST | `/api/question-bank/questions/:id/options/bulk/` | Bulk sync options (create+update+delete in one request) |
| GET/POST | `/api/question-bank/questions/:id/options/` | List/create response options |
| GET/POST | `/api/question-bank/questions/:id/media/` | List/create media files (audio/video) |
| GET/POST | `/api/question-bank/questions/:id/flash-items/` | List/create flash items (text/image) |
| GET/POST | `/api/question-bank/questions/:id/hotspots/` | List/create hotspot areas |

## 21 Question Types

| Code | Type | Editor |
|---|---|---|
| MCQ_TEXT_IMAGE | 1a: MCQ – Text/Image | MCQEditor |
| MCQ_TEXT_IMAGE_IMG_OPTIONS | 1b: MCQ with Image Options | MCQEditor |
| MCQ_AUDIO_MULTI | 1c: MCQ – Audio | MCQEditor |
| MCQ_VIDEO_MULTI | 1d: MCQ – Video | MCQEditor |
| MCQ_WORD_FLASH_MULTI | 1e: MCQ – Word Flash | MCQEditor + FlashItemsEditor |
| MCQ_IMAGE_FLASH_MULTI | 1f: MCQ – Image Flash | MCQEditor + FlashItemsEditor |
| MCQ_PASSAGE_DISPLAY_MULTI | 1g: MCQ – Passage Display | MCQEditor |
| MCQ_IMAGE_DISPLAY_MULTI | 1h: MCQ – Image Display | MCQEditor |
| FITB_SINGLE | 2a: FITB – Single Field | FITBEditor |
| FITB_MULTI_FIELD | 2b: FITB – Multiple Fields | FITBEditor |
| FITB_WORD_FLASH_MULTI | 2c: FITB – Word Flash | FITBEditor + FlashItemsEditor |
| FITB_IMAGE_FLASH_MULTI | 2d: FITB – Image Flash | FITBEditor + FlashItemsEditor |
| MATCH_FOLLOWING | 3: Match-the-Following | MatchEditor |
| GRID_LIST_SELECTION | 4: Grid-List Selection | GridEditor |
| HOTSPOT_SINGLE | 5a: Hotspot – Single | HotspotEditor |
| HOTSPOT_MULTI | 5b: Hotspot – Multi | HotspotEditor |
| RANK_SIMPLE | 6a: Simple Ranking | RankEditor |
| RANK_THEN_RATE | 6b: Rank-then-Rate | RankRateEditor |
| STANDARD_RATING_SCALE | 7: Rating Scale | RatingEditor |
| FORCED_CHOICE_SINGLE_LEVEL | 8a: Forced-Choice Single | ForcedChoiceEditor |
| FORCED_CHOICE_TWO_LEVEL | 8b: Forced-Choice Two-Level | ForcedChoiceEditor |

## 9 Scoring Modes

| Code | Description |
|---|---|
| BINARY | 0 or 1 (exact match) |
| BINARY_FUZZY | 0 or 1 with fuzzy match threshold (FITB) |
| PARTIAL | Partial credit per correct option (MCQ multi, Match) |
| NEGATIVE | Negative marking for wrong answers |
| RANK | Rank scoring (Rank questions) |
| RANK_RATE | Rank + rate combined scoring |
| RATING | Rating scale scoring (no right/wrong) |
| FORCED_CHOICE | Forced-choice scoring (predefined score per statement) |
| FORCED_CHOICE_RATED | Forced-choice + rating combined |

## Review Workflow

```
draft → pending_content_review → content_reviewed → pending_psychometric_review → confirmed
                ↑                        |                        |
                |_______ send_back ______|________________________|
```

- **SME**: creates/edits own questions (draft/sent_back only); submits for review
- **Reviewer**: reviews content (approve → psychometric review; send_back → SME; reject)
- **Psychometrician**: reviews psychometric properties (approve → confirmed; send_back → SME; reject)
- **cj_admin**: can edit/delete any question regardless of status (override)

## Models

- **Category**: hierarchical (parent FK), name, description, is_active
- **Question**: 21 types, 9 scoring modes, review status, psychometric properties, exposure limit
- **ResponseOption**: TEXT/IMAGE/MATCH_A/MATCH_B/DRAG_POOL/RANK/FORCED_CHOICE types
- **CorrectAnswer**: multiple correct answers for FITB (up to 5 per field)
- **MediaFile**: audio/video files (stored as URL or base64 data URL)
- **FlashItem**: text/image items for flash question types
- **HotspotArea**: pixel-defined click zones for hotspot questions
- **QuestionReview**: review action history (reviewer, type, action, comment, rating)

## Frontend

- **QuestionBankPage** (`/question-bank`): list with filters, search, pagination, category filter, edit/delete/submit actions
- **QuestionDetailPage** (`/question-bank/:id`): 5 tabs (Details, Options, Media, Reviews, Preview)
- **QuestionEditorPage** (`/question-bank/new` and `/question-bank/:id/edit`): full-page editor with type-specific sub-editors
- **CategoryManager** (embedded in QuestionBankPage via modal): tree view + CRUD for categories

## Permissions

| Role | View | Create | Edit | Delete | Review |
|---|---|---|---|---|---|
| cj_admin | ✅ all | ✅ | ✅ all | ✅ all | ✅ |
| psychometrician | ✅ all | ✅ | ✅ draft/sent_back | ❌ | ✅ psychometric |
| sme | ✅ own | ✅ | ✅ draft/sent_back | ✅ draft/sent_back | ❌ |
| reviewer | ✅ all | ❌ | ❌ | ❌ | ✅ content |
| individual | ❌ | ❌ | ❌ | ❌ | ❌ |

## Image/Media storage

Images, audio, and video are stored as **base64 data URLs** or **external URLs** in TextField columns (not as multipart file uploads). This simplifies the frontend MediaManager and avoids file storage infrastructure. The following fields accept base64 data URLs:
- `Question.image`
- `ResponseOption.image_file`
- `FlashItem.image_file`
- `MediaFile.file`

## Not yet frozen

This module is still in active development. The API contract may change. Once the assessment module (which consumes questions) is complete, this module will be frozen at v1.0.0.
