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

---

### 5. System Testing & Review Feedback Report 2 (Psychometric)
- **File:** `docs/review-docs/System Testing & Review Feedback Report 2 _ 25-07-2026.pdf`
- **Date received:** 25 July 2026
- **Source:** Client testing team (8-page report with screenshots)
- **Status:** ✅ All items resolved
- **Commit:** `1816a79`
- **Resolution summary:**

#### Common Issues (3 items)
| Ref | Issue | Status |
|---|---|---|
| C-1 | Question Text 2 should be optional (not always required) | ✅ Done (already optional) |
| C-2 | Text formatting (italics, bold, font size) | ✅ Done (WysiwygEditorLite) |
| C-3 | Section tagging per option for psychometric types | ✅ Done (section_tag field) |

#### Simple Ranking Scale (6a) — 2 items
| Ref | Issue | Status |
|---|---|---|
| 1 | Each option tagged to a different Section | ✅ Done (section_tag field on ResponseOption) |
| 2 | Scoring: rank value = N - rank_position. Section summary = sum per section | ✅ Done (_score_rank rewritten) |

#### Rank-Then-Rate Scale (6b) — 2 items
| Ref | Issue | Status |
|---|---|---|
| 1 | Same section tagging as Simple Rank | ✅ Done |
| 2 | Scoring: rank_value x rating_value. Section summary | ✅ Done (_score_rank_rate rewritten) |

#### Forced-Choice Single Level (8a) — 3 items
| Ref | Issue | Status |
|---|---|---|
| 1 | Two options tagged to DIFFERENT sections | ✅ Done (section_tag field) |
| 2 | Score = selection vs non-selection (not predefined per option) | ✅ Done (selection_score, non_selection_score fields) |
| 3 | Scoring: selected gets selection_score, unselected gets non_selection_score | ✅ Done (_score_forced_choice rewritten) |

#### Forced-Choice with Rating (8b) — 3 items
| Ref | Issue | Status |
|---|---|---|
| 1 | Same pairing rules as 8a | ✅ Done |
| 2 | Same scoring method as 8a | ✅ Done (selection_score, non_selection_score) |
| 3 | Selected: selection_score x rating. Unselected: non_selection_score | ✅ Done (_score_forced_choice_rated rewritten) |

---

### 6. System Testing & Review Feedback Report 3 (Training + Counselling)
- **File:** `docs/review-docs/System Testing & Review Feddback Report 3 _ 30-07-2026.pdf`
- **Date received:** 30 July 2026
- **Source:** Client testing team (17-page report with screenshots)
- **Status:** 🔄 In progress — implementing

#### Training Issues
| # | Issue | Status |
|---|---|---|
| 1.1 | Individual user registration form for courses | 🔄 Pending |
| 1.2 | To-and-fro notification system post-registration | 🔄 Pending |
| 1.3 | Payment process viewable | 🔄 Pending |
| 1.4 | Course structure view post-registration | 🔄 Pending |
| 1.5 | Post-payment notification to trainer + admin | 🔄 Pending |
| 2.1 | Course commencement logic (online standard vs live) | 🔄 Pending |
| 2.2 | Training dashboard (completion status, time tracker, score) | 🔄 Pending |
| 2.3 | Resume course from last position | 🔄 Pending |
| 3.1 | Add/Edit assignment features | 🔄 Pending |
| 3.2 | Embed external links in content | 🔄 Pending |
| 3.3 | Last date for assignment submission | 🔄 Pending |
| 3.4 | Report submission mandatory/non-mandatory toggle | 🔄 Pending |
| 3.5 | Report submission feature | 🔄 Pending |
| 3.6 | File upload (PDF/PPT/Word) for report submission | 🔄 Pending |
| 3.7 | Text formatting for report entry field | 🔄 Pending |
| 3.8 | Trainer evaluation: 10-point rating + feedback text | 🔄 Pending |
| 4.1 | Trainer can create assessments (not just select from pool) | 🔄 Pending |
| 4.2 | Only trainer's own assessments visible | 🔄 Pending |
| 4.3 | Link assessment to specific session/topic/lesson | 🔄 Pending |
| 4.4 | Assessment report viewable to individual + trainer | 🔄 Pending |
| 5.1 | Course content sequencing | 🔄 Pending |
| 5.2 | Set course completion parameters | 🔄 Pending |
| 6.1 | Trainer request course update (admin approval) | 🔄 Pending |
| 6.2 | Trainer request course deletion (admin approval) | 🔄 Pending |
| 6.3 | Show upcoming live sessions on trainer page | 🔄 Pending |
| 6.4 | Trainer reschedule session | 🔄 Pending |
| 6.5 | Schedule session on candidate request | 🔄 Pending |
| 6.6 | Post-scheduling notification to individual user | 🔄 Pending |

#### Online Standard Course Issues
| # | Issue | Status |
|---|---|---|
| 1 | Add content (text/audio/video/links) + content config | 🔄 Pending |
| 2 | Interactive questions during video/audio | 🔄 Pending |
| 3 | Embed video/audio links in text | 🔄 Pending |
| 4 | Live session scheduling post-registration | 🔄 Pending |

#### Online Live Course Issues
| # | Issue | Status |
|---|---|---|
| 1 | Advance vs ongoing scheduling | 🔄 Pending |
| 2 | Reschedule in emergencies | 🔄 Pending |
| 3 | To-and-fro notification | 🔄 Pending |

#### Counselling Issues
| # | Issue | Status |
|---|---|---|
| 1.1 | Edit timeslots | 🔄 Pending |
| 1.2 | Timeslot limit (3 weeks) | 🔄 Pending |
| 1.3 | At least 1 week timeslots available + notification | 🔄 Pending |
| 1.4 | Text formatting for counsellor biodata | 🔄 Pending |
| 1.5 | Upload passport-size photograph | 🔄 Pending |
| 1.6 | Fields: gender, language, geographical location | 🔄 Pending |
| 1.7 | Counsellor info visible to individual user | 🔄 Pending |
| 1.8 | Registration form on booking | 🔄 Pending |
| 1.9 | Terms & Policies text field for CJ Admin | 🔄 Pending |
| 1.10 | Booking confirmation notification | 🔄 Pending |
| 1.11 | Cancellation/refund policy display | 🔄 Pending |
| 1.12 | Counsellor confirms booking within 6 hours | 🔄 Pending |
| 1.13 | Confirmation/cancellation notification | 🔄 Pending |
| 1.14 | Track counsellor booking cancellations | 🔄 Pending |
| 1.15 | Individual user cancellation + refund policy | 🔄 Pending |
| 1.16 | Cancellation reason text field | 🔄 Pending |
| 1.17 | Counsellor tagged to counselling categories | 🔄 Pending |
| 1.18 | Remove My Sessions from counsellor page | 🔄 Pending |

#### Counselling Delivery Issues
| # | Issue | Status |
|---|---|---|
| 1 | Countdown reminder on dashboard | 🔄 Pending |
| 2 | Feedback form (8 questions) | 🔄 Pending |
| 3 | Feedback available to CJ Admin only | 🔄 Pending |
| 4 | Session Summary form (6 fields) | 🔄 Pending |
| 5 | Followup session scheduling | 🔄 Pending |
| 6 | Followup session notification | 🔄 Pending |
| 7 | Followup session booking notification | 🔄 Pending |
| 8 | Followup session payment reminder | 🔄 Pending |
