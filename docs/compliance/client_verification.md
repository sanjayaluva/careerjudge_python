# Career Judge — Verification Guide (Reports 3, 4 & 5)

**Purpose.** A factual, code-verified status map of the client's review-report
items — so completion can be checked independently by running a test or
following UI steps. It is **not** a blanket "complete" claim. Every Report 4 &
Report 5 line below was verified by reading the actual code (file evidence on
request).

**Run the automated checks:** `bash scripts/verify_client.sh` (needs
`backend/.venv`). Green = the behaviour is locked by a test.

**Legend:** ✅ Done · 🟡 Partial · 🔴 Not done · ❔ Unclear.

**Scope note up front.** All **corporate org-scoping** (multi-tenant
organisations, and per-org visibility/tagging for Corp Admin, Group Admin, Corp
Exclusive and Channel Partner) is **not implemented** — verified: *no backend
query is filtered by the user's organisation anywhere*; the `OrganizationMember`
/ `OrganizationAssignment` / `DomainCategory` models exist but are not wired to
any API. This was the **separate corporate change-order** and is the bulk of
Report 4 roles 1–4. It should be stated plainly to the client.

---

## A. The two issues the client named as critical

**A1. Assessment linking to a specific session/topic/lesson** — ✅ **Fixed.**
The form now has a session/topic/lesson picker (per level); the serializer
validates the target matches the level. Tests: `test_assessment_links_to_specific_session`,
`test_assessment_links_to_topic_and_lesson`.

**A2. Psychometric section-tagging (author flow)** — 🔴 **Not to spec (client is
right).** System implements the client's deprecated *Approach 2* (options
back-tagged via `ResponseOption.section_tag`), not *Approach 1* (statements
authored in the QnBank first, grouped at config time). Scoped separately in
`docs/compliance/psychometric_approach1_scope.md` (~11–12 dev-days).

---

## B. Report 5 — Assessment Parameter Setting (10 items: 8 ✅ · 1 🟡 · 1 🔴)

| Item | Status | Evidence / note |
|---|---|---|
| Timer §1 — timers at Level 1–4 + Question level | ✅ | `TIMER_LEVEL_CHOICES`; section & question `duration_seconds`; player honours both |
| Timer §2 — durations sum upward; higher levels not user-set | 🟡 | Sum-upward done (`aggregate_duration_seconds`); **no guard** stops a duration being entered on a higher-level section |
| Order §1 — display order per level (randomise within a level) | ✅ | `AssessmentSection.order_mode` STATIC/RANDOM + per-section shuffle in player |
| Order §2 — "static as configured" sequential editable view | ✅ | STATIC choice + editable section order |
| Assign §1 — questions attach only at the leaf section | ✅ | `not_leaf_section` guard (psychometric exempt). Test-backed |
| Assign §2 — section list shows full path chains | ✅ | **Fixed** — picker now shows `A ›› B ›› Leaf` chains |
| Assign §3 — parent not listed when a child exists | ✅ | **Fixed** — picker lists leaf sections only |
| Assign §4 — one question assigned **only once** per assessment | ✅ | `question_already_assigned` guard (just added). Test-backed |
| Assign §5 — psychometric author flow (Approach 1) | 🔴 | See **A2** |
| Delivery — random N from the assigned pool, leaf only | ✅ | `delivery_count` + `random.sample` per session; note: over-count is soft-clamped, no hard validation error |

---

## C. Report 4 — roles 5–11 (the non-corporate roles)

### Role 5 — SME (5 ✅ · 1 🟡 · 1 🔴)
| # | Status | Note |
|---|---|---|
| 1 sees only own questions | ✅ | `get_queryset` forces `created_by=self` for sme |
| 2 no create-categories | ✅ | category UI gated to psychometrician/cj_admin |
| 3 no view/take assessments | ✅ | **Fixed** — Assessments removed from SME nav + grant |
| 4 pick specific Reviewer **and Psychometrician** (domain) | 🟡 | Auto-routes to a **domain reviewer**; no *manual* choice and **no psychometrician routing** (`assigned_psychometrician` doesn't exist) |
| 5 create question from task (auto-fill hyperlink) | ✅ | Task → "Create question from spec" prefills type/category |
| 6 live-chat · 7 invoice | ✅ | present |

### Role 6 — Reviewer (6 ✅ · 1 🟡 · 3 🔴)
| # | Status | Note |
|---|---|---|
| 1 sees only assigned questions | 🟡 | Sees own + all non-draft pipeline; assigned-only is opt-in (`?assigned=me`) |
| 2 rename tab → "My Review Questions" | ✅ | **Fixed** — nav + page heading renamed for reviewers |
| 3 no create-categories | ✅ | gated |
| 4 no view/take assessments | ✅ | **Fixed** — Assessments removed from Reviewer nav + grant |
| 5 receive only own-domain questions | ✅ | domain routing via `domain_root` + `assigned_reviewer` |
| 6 sent-back returns to same SME | ✅ | `created_by` never reassigned |
| 7 **no rating when sending back** | ✅ | **Fixed** — rating hidden + ignored on send-back/reject. Test-backed |
| 8 second-round rating replaces old (history kept) | ✅ | each review is a new row; latest effective, all retained |
| 9 live-chat · 10 invoice | ✅ | present |

### Role 7 — Individual User (2 ✅ · 8 🟡 · 6 🔴 · 2 ❔)
| # | Status | Note |
|---|---|---|
| 1 view/take only registered+paid assessments | 🟡 | Sessions scoped to self + start is pay-gated, but the **list shows all published**, not paid-only |
| 2 unpaid → **login popup** + Pay Now | 🟡 | Pay-gate + Pay Now exist, shown as a **toast**, not a login popup |
| 3 registration form w/ profile autofill | 🔴 | No such form; profile has only `full_name` |
| 4 assessment tabs Not-Attempted/Suspended/Completed | 🔴 | It's a table with a status column, not tabs |
| 5–7 mandatory registration fields (First/Last/Gender…) | 🔴 | No registration form / field set |
| 8 only paid+published profiling solutions | ❔ | No explicit paid-only filter observed |
| 9 profiling tabs Not-Attempted/Suspended/Completed | 🔴 | Detail page tabs are authoring, not status |
| 10 sees only own reports | ❔ | No individual-facing own-reports list confirmed |
| 11 Download-PDF button | 🟡 | PDF endpoint exists; no individual-facing button confirmed |
| 12 view only paid courses | 🟡 | Course start pay-gated; browse shows all published |
| 13 unpaid course → popup + Pay Now | 🟡 | Redirects to checkout, not a popup |
| 14 training tabs New/Ongoing/Completed | 🔴 | Tabs are Browse/Manage/My-Sessions |
| 15 reorder course tabs + rename Created-by→Trainer + add Assignments | 🟡 | Registrations already hidden; **no Assignments tab**, "Created by" not renamed |
| 16 only paid counselling · 17 unpaid popup | 🟡 | Booking is payment-aware; no paid-only browse / explicit popup |
| 18 booking notifies counsellor (was a bug) | ✅ | **Fixed** — `notify_user(counsellor…)` on booking |
| 19 "Counsellor" link → error page (was a bug) | ✅ | **Fixed** — `counseling/:id` route added |
| 20 rename module tabs (My Assessments, …) | 🔴 | Not renamed |
| 21 "/hr"→"/Session", **dollars → rupees** | ✅ | **Fixed** — counselling shows ₹…/Session (INR) |

### Role 8 — Trainer (7 ✅ · 3 🟡 · 3 🔴)
| # | Status | Note |
|---|---|---|
| 1 sees only own courses | 🔴 | No owner scoping — trainer sees all courses |
| 2 remove "My Courses"; add Preview | 🟡 | Relabelled; but no content-preview for trainer |
| 3 create structure first time, locked after publish | ✅ | draft ungated, published gated |
| 4 request-to-modify + edit after approval | ✅ | `CourseModificationRequest` flow |
| 5 rich-text on Text Content | 🔴 | Content body is a plain textarea (WYSIWYG only on course description) |
| 6 edit content after adding | 🔴 | No edit-body flow (only reorder / retitle) |
| 7 timeline/interactive questions | ✅ | Timeliner present |
| 8 trainer **creates** assessment (training-only) | 🟡 | Backend perms exist + own-scoping; **frontend Create is gated off for trainer**; only links existing published assessments |
| 9 link to specific session/topic/lesson | ✅ | **Fixed** (A1) |
| 10 verify "Notify" reached the user (was a bug) | ✅ | **Fixed** — notify action confirmed |
| 11 live-chat · 12 invoice | ✅ | present |

### Role 9 — Counsellor (5 ✅ · 4 🟡 · 5 🔴 · 2 ❔)
| # | Status | Note |
|---|---|---|
| 1 no assessment tab · 2 no profiling tab | ✅ | **Fixed** — both removed from Counsellor nav + grant |
| 3 reports limited to his clients · 4 no create-report · 5 only booked-client reports | 🔴/❔ | No counsellor/client scoping on reports; create not blocked |
| 6 no browse/book | 🟡 | Browse tab still shown; book/My-Sessions hidden |
| 7 tagged to a counselling category | ✅ | `CounsellorProfile.categories` M2M |
| 8 timeslots min 1 wk / max 3 wks | 🟡 | **Max 3wk enforced; min 1wk not** |
| 9 timeslots in table format · 10 booked in weekly format | 🔴 | Flat list, no table / weekly grouping |
| 11 remove "My Sessions" | ✅ | hidden for counsellor |
| 12 post-booking notification | ✅ | notifies counsellor |
| 13 ZOOM setup | 🟡 | Manual meeting-link field, not Zoom API |
| 14 post-ZOOM notification to counselee | ✅ | on confirm |
| 15 live-chat | 🔴 | **not** in counsellor visibility |
| 16 invoice | ✅ | present |

### Role 10 — Psychometrician (5 ✅)
Analysis engine + QB + assessments + career-profiling + reporting all present
and role-visible. ✅ all five.

### Role 11 — CJ Admin (8 ✅ · 2 🟡 · 5 🔴)
| # | Status | Note |
|---|---|---|
| 1–4 tag Corp/Group/Excl/Partner to org | 🟡 | User↔org via `OrganizationMember` works; the higher-level tagging UIs are thin/absent (corporate) |
| 5 tag Reviewer to domain · 7 tag SME to domain | 🟡 | Domain routing is **inferred** from authored questions; **no explicit admin domain-tag** (`DomainCategory` orphaned) |
| 6 add new domains | 🔴 | `DomainCategory` has no CRUD API |
| 7b tag Counsellor to category | ✅ | done |
| 8 Edit-User button | ✅ | present |
| 9 task assignment functional | ✅ | `TaskViewSet.create` + assignee picker |
| 10 create Parent Task | ✅ | `parent_task` FK + picker |
| 11 one task → multiple question specs | ✅ | `TaskSpec` is one-task-many-specs |
| 12–14 assign assessments/trainings/counselling to a Corp Org | 🔴 | `OrganizationAssignment` model exists but **no API** (corporate) |
| 19 approve/send-back invoices · 20 confirm payment | ✅ | present |
| 21 message any user | ✅ | messaging present |

*(Role 12 Helpdesk — the client marked "not available for checking"; nothing to verify.)*

---

## D. Roles 1–4 (Corporate) — 🔴 not implemented (separate change-order)

Verified: no org-scoped filtering exists; corporate models are orphaned. A few
**adjacent, non-scoping** items do work and are usable: bulk-upload of users
(gated by `accounts.add`), invoice create/revise/cancel, and payment history.
Everything that depends on *"restrict this role to its own organisation's
data"* — the substance of Report 4 roles 1–4 — is pending and belongs to the
corporate change-order.

---

## E. Quick wins — status

**Done this pass** (committed, tests green where applicable):
1. ✅ Reviewer no longer rates on send-back (6.7) + tab renamed "My Review Questions" (6.2).
2. ✅ Assessments removed from SME/Reviewer nav+grant (5.3/6.4); Assessments & Profiling removed from Counsellor (9.1/9.2).
3. ✅ Currency $ → ₹ and "/hr" → "/Session" across counselling (7.21).
4. ✅ Section picker: leaf-only + full path chains (Report 5 §3.2/§3.3).

**Deferred — larger than a quick win** (flagged, not done):
- 🔴 Counsellor "minimum 1 week of slots" (9.8) — this is a reminder/notification
  to the counsellor + helpdesk when availability runs short (Report 3 Counselling
  §3), not a per-slot check; belongs with the notifications work.
- 🔴 Individual **status tabs** (Not-Attempted / Suspended / Completed) for
  assessments, profiling and training (7.4/7.9/7.14) — a UI restructure per module.

**Bigger, discrete items** (separate builds): the **psychometric Approach-1 flow**
(scoped separately), **trainer-authored assessments** (8.8), **explicit domain
tagging + DomainCategory CRUD** (11.5/6/7), and the whole **corporate change-order**.

## F. Suggested agenda for the meeting
1. Agree the **scope split in writing**: (a) SRS + Reports 1–3, (b) Report 4
   role-permission scoping, (c) corporate platform, (d) Report 5 params.
2. **Run `scripts/verify_client.sh` live** for the test-backed items.
3. Walk this table top-to-bottom as the shared **done / pending list**.
4. Approve the two discrete builds (psychometric Approach-1; and, if wanted, the
   Report 4 non-corporate role-scoping) with the estimates.

*Intentionally candid. Review before sharing; adjust framing to suit the
commercial conversation.*
