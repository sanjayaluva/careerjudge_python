# CareerJudge — Review Document Tracking

> **Purpose:** Tracks all client review documents received, their issues,
> and the resolution status. Serves as a permanent reference of work done
> per client feedback.
>
> Last updated: 30 July 2026

---

## Review Documents Received

### 1. SRS (System Requirements Specification)
- **File:** `docs/review-docs/SRS.pdf` (10.3 MB, 23 pages)
- **Date received:** 2 July 2026
- **Source:** Client provided as the original requirements document
- **JSON specs:** Extracted into `specs/cj_jsons/` (15 JSON files)
- **Status:** ✅ Fully implemented
- **Resolution:** All 46 use cases (UC001–UC051) implemented across 13 modules.
  See `docs/PROJECT_STATUS.md` for module-by-module status.

---

### 2. Admin User System Administration Process
- **File:** `docs/review-docs/9. Admin User_System Administration Process.pdf`
- **Date received:** 2 July 2026
- **Source:** Client provided as part of the original spec set
- **JSON spec:** `specs/09_admin_system_administration.json`
- **Status:** ✅ Fully implemented
- **Resolution:** Task Management module (apps/tasks/) built with:
  - Task + TaskSpec + TaskProgressUpdate + TaskExtensionRequest models
  - Assign task to SME/Reviewer/Psychometrician/Trainer/Counsellor
  - Monitor progress, cancel with reason, approve completion
  - Extend due date with admin approval
  - 24 backend tests
  - Frontend: TasksPage + TaskDetailPage with tabs + Assign Task modal

---

### 3. System Testing & Review Feedback Report
- **File:** `docs/review-docs/System Testing & Review Feedback Report _ 24-07-2026.pdf`
- **Date received:** 24 July 2026
- **Source:** Client testing team (23-page report with screenshots)
- **Status:** ✅ All 67 items resolved
- **Implementation status PDF:** `docs/review-docs/CareerJudge_Feedback_Status_Response.pdf`
- **Resolution summary:**

#### Common Configuration Issues (2 items)
| Ref | Issue | Status |
|---|---|---|
| C-CFG-1 | Multi-question pooling under single media | ✅ Done |
| C-CFG-2 | Rich-text formatting for question text fields | ✅ Done |

#### Common Front-end Issues (10 items)
| Ref | Issue | Status |
|---|---|---|
| C-FE-1 | Multi-answer scoring (+1/-1, min 0) | ✅ Done |
| C-FE-2 | Text 1 above media, Text 2 below | ✅ Done |
| C-FE-3 | Timed presentations cannot be replayed | ✅ Done |
| C-FE-4 | Text 2 + options appear only after presentation | ✅ Done |
| C-FE-5 | Previous button: no replay on revisit | ✅ Done |
| C-FE-6 | Larger images | ✅ Done |
| C-FE-7 | Multi-column option layout (1/2/3 columns) | ✅ Done |
| C-FE-8 | Flash content changes between questions | ✅ Done |
| C-FE-9 | Hide backend details from candidate | ✅ Done |
| C-FE-10 | Bigger timer display | ✅ Done |
| Rec 1 | Timed vs Unlimited display mode | ✅ Done |
| Rec 2 | Replay Permitted vs Not Permitted | ✅ Done |

#### MCQ Question Types 1a–1h (22 items)
All 22 items resolved. Key changes:
- Multi-sub-question pooling for Audio (1c), Video (1d), Passage (1g)
- Rich-text formatting for Image Display (1h)
- Timed play button for Image Display
- No-replay enforcement for audio/video
- Flash replay locking
- Duplicate passage body removal

#### Fill-in-the-Blank Types 2a–2d (14 items)
All 14 items resolved. Key changes:
- Question Text 2 field added to FITB editor
- Flash specifications hidden from candidate
- Bigger centred Play button
- Larger flash images
- Replay disabled when configured
- Flash content no longer repeats between questions
- Revisit-no-replay enforced
- FITB flash any-order scoring (union of correct answers)

#### Match-the-Following (3 items)
All 3 items resolved:
- Dummy options (MATCH_DUMMY type) + Group B shuffle
- "Add Dummy Option" button in editor

#### Grid Selection (7 items)
All 7 items resolved:
- Numbered-button grid UI with cell popups
- Row/column labels hidden
- Question Text 2 field added
- "View Complete Grid Items" button
- Correct +1/-1 scoring

#### Hotspot (4 items)
All 4 items resolved:
- +1/-1 scoring for multi-hotspot
- Transparent/visible spot-marking toggle
- Click-accuracy tolerance (5px, all 3 shape types)
- Duplicate image removed

#### Final Page (2 items)
Both resolved: bigger timer, hidden backend details.

---

### 4. Multiple Questions Display Style
- **File:** `docs/review-docs/Multiple Questions Display style.pdf`
- **Date received:** 25 July 2026
- **Source:** Client provided as a UI mockup specification
- **Status:** ✅ Fully implemented
- **Resolution:**

| Requirement | Status | Details |
|---|---|---|
| Two-phase display (media → sub-questions) | ✅ Done | Media phase with Show Content button, then sub-questions appear |
| Sub-questions managed by question itself | ✅ Done | Single AssessmentQuestion row; player handles sub-question navigation |
| In-question sub-question navigation | ✅ Done | Next/Previous cycles through sub-questions within a question |
| Per-sub-question text field | ✅ Done | `sub_question_texts` JSON field (separate from Text 2) |
| Layout: Text 1 → Media → Text 2 → SubQ Text → Options | ✅ Done | Correct rendering order in player |
| Media only on sub-question 0 | ✅ Done | `isFirstSubQ` gate on media rendering |
| Sub-questions in order 1, 2, 3 | ✅ Done | Sequential navigation, no random order |
| Timer starts only on button click (passage) | ✅ Done | `secondsLeft` starts as null, set on startPresentation() |
| Image hidden + Show Content button + timer | ✅ Done | ImageDisplayTimed always used for MCQ_IMAGE_DISPLAY_MULTI |
| Anti-cheating audio/video player | ✅ Done | No download, no seek, play-once button |
| Navigation locked during presentation | ✅ Done | Previous/Next/sidebar disabled while presentationActive |
| No skip presentation button | ✅ Done | Removed — candidate must play content to proceed |
| Submit loading overlay | ✅ Done | Full-screen spinner with "Submitting your assessment…" message |
| Correct scoring (parent = wrapper, sub-questions = 0 or 1 each) | ✅ Done | Placeholder attempts created for unattempted sub-questions |
| Assessment summary counts (Total/Answered/Remaining) | ✅ Done | totalQuestions sums sub_question_count across all questions |

---

## Screenshots Received

| File | Description | Date |
|---|---|---|
| `screenshot-audio-player-missing.png` | Audio player not showing during assessment delivery | 27 July 2026 |
| `screenshot-audio-player-still-missing.png` | Audio player still not showing (case mismatch bug) | 29 July 2026 |

Both issues resolved:
1. Fixed `file_url` → `file` field mismatch (backend returns `file`, frontend expected `file_url`)
2. Fixed `media_type` case mismatch (backend stores `"AUDIO"` uppercase, frontend compared with `"audio"` lowercase)

---

## Pending Review Documents

| Document | Status | Expected Content |
|---|---|---|
| Psychometric Questions Review | ⏳ Not yet received | Review of psychometric question types (Rating, Rank, Forced-Choice) + analysis |
| Course & Counselling Review | ⏳ Not yet received | Review of Training module (SRS 07) + Counseling module (SRS 08) |

These will be analyzed and implemented when provided by the client.

---

## Commits Log (Key Recent Commits)

| Commit | Date | Description |
|---|---|---|
| `5de04d3` | 30 Jul | Disable all navigation while content is playing |
| `a6ed84c` | 30 Jul | Remove skip button + add submission loading overlay |
| `3d6d12b` | 30 Jul | Ensure all sub-question attempts exist before scoring |
| `b60c691` | 30 Jul | Anti-cheating audio/video player (no download, no seek) |
| `a2fb344` | 29 Jul | Fix media_type case mismatch (AUDIO vs audio) |
| `e107ecc` | 29 Jul | Audio/video player rendering + presentation gating + skip button |
| `16b9b32` | 28 Jul | Fix file_url field mismatch + remove duplicate preview |
| `4fa1b9a` | 28 Jul | Image show button + Text2 not gated + assessment readiness refresh |
| `0be4b74` | 28 Jul | Passage timer starts on button click + image show button + previews |
| `1eca271` | 27 Jul | In-question sub-question navigation + separate sub_question_text field |
| `e09d990` | 26 Jul | Implement Multiple Questions Display Style per spec doc |
| `7bd7ce5` | 26 Jul | WYSIWYG HTML rendering + multi-sub-question pooling end-to-end |
| `8586395` | 26 Jul | Add .npmrc for Vercel build (legacy-peer-deps) |
| `ddc0ac7` | 25 Jul | Close all remaining feedback gaps (12 gaps → 0) |
| `4efb91f` | 24 Jul | Close SRS 09 Task Management module + all feedback items |
