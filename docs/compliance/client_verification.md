# Career Judge — Verification Guide (Reports 3, 4 & 5)

**Purpose.** This maps the client's review-report items to **what the code and
the automated tests actually show today** — so the completion of each item can
be checked independently, by running a test or by following UI steps. It is a
factual status map, **not** a blanket "everything is complete" claim. Where an
item is only partly done or not done, it says so.

**How to run the automated checks.** From the repo root:

```
bash scripts/verify_client.sh
```

Each block runs the real test(s) that prove one report item. "passed" means the
behaviour is implemented and locked by a test. (Any `weasyprint` failures are a
missing PDF native library in the test machine — cairo/pango — not a product
defect.)

**Legend:** ✅ Done & test-backed · 🟡 Partial · 🔴 Not done / not to spec ·
❔ Needs a line-by-line pass to confirm.

---

## A. The two issues the client named as critical

### A1. Assessment linking to a specific session/topic/lesson
*(Report 3 §4 Issue 3 · Report 4 Trainer Issue 9)* — **✅ Now fixed.**

- **Was**: the "Link Assessment" form let the trainer choose a *level label*
  (End of Session / Topic / Lesson) but not *which* session. The client was
  correct.
- **Now**: the form shows a **session picker** (Lesson › Topic › Session) and
  requires it for every level except *End of Course*; the linked session is
  shown in the assessments table.
- **Verify (test)**: `test_assessment_links_to_specific_session`.
- **Verify (UI)**: Trainer → a draft course with lessons/topics/sessions →
  Assessments tab → *Link assessment* → pick level *End of Session* → the
  **Session** dropdown appears → pick a session → Link → the row shows the
  session name under the level.
- **Still open (honest note)**: the underlying model links to a *session*. For
  *End of Topic* / *End of Lesson* the trainer picks a session inside that
  topic/lesson; if the client requires a direct topic-level or lesson-level
  target (no session), that is a small further change — flag it if so.

### A2. Psychometric question-type **section-tagging** (author flow)
*(Report 5 §3 Issue 5)* — **🔴 Not to spec. The client is correct.**

- The client asked for **Approach 1**: psychometric **statements are authored
  and category-tagged in the Question Bank first** (single statements, no
  options), then **drawn into the assessment and grouped into Rank groups /
  Forced-Choice pairs at configuration time**, with the section derived from the
  Question Bank category. This lets SMEs create and Reviewers review.
- The system currently implements **Approach 2** (the one the client explicitly
  called error-prone): options are typed into a Rank/Forced-Choice template and
  each option is **back-tagged to a section** (`ResponseOption.section_tag`,
  `_ensure_section_tags_have_sections`). This forces a single psychometrician to
  do everything and cannot use SMEs/Reviewers.
- **This is a genuine, sizeable pending item** — a new authoring + assessment-
  configuration flow, not a small fix. It should be scoped and estimated
  separately.

---

## B. Report 5 — Assessment Parameter Setting (item by item)

| Item | Status | How to verify |
|---|---|---|
| §1 Multi-level timers (Level 1–4 + Question level, summing upward) | 🟡 Partial | Per-section timer + per-section order exist; the **level-summing timer model** the report describes is **not** fully built. Needs confirmation against Doc 3 §5.2. |
| §2 Order setting per level (randomise within a level) | 🟡 Partial | Per-section `order_mode` (STATIC/RANDOM) exists; the "show all levels in sequential editable flow" view does not. |
| §3.1 Questions attach only at the **leaf** section | ✅ Done | `test_cannot_assign_question_to_non_leaf_section`, `test_section_fifth_level_rejected` |
| §3.2 Section list shows full path chains | ❔ | Needs UI confirmation. |
| §3.3 Parent not listed when a child exists | ❔ | Needs UI confirmation. |
| §3.4 One question assigned **only once** per assessment | 🔴 Not done | DB blocks the same question twice in the **same** section only, not across sections. |
| §3.5 Psychometric author flow (Approach 1) | 🔴 Not done | See **A2**. |
| §4 Delivery count (random N from the assigned pool, leaf only) | 🟡 Partial | `delivery_count` field + player selection exist; the leaf-only + max-count validation rules need confirmation. |

---

## C. Modules the client said they are "in the dark" about

### Reporting — 🟡 substantially built, verifiable
Built this cycle: question-level data breakdown, chart/graph rendering, report
templates + in-app live preview, band creation for all target types (FMI / PMI
/ VMI / raw / PMI-D), and the full profiling-report config (include-index
toggles + PMI-D order). **Verify (test)**:
`apps/reporting/tests/test_question_level_and_charts.py` and the wider
`apps/reporting` suite. Open item: PDF rendering can't run in this environment
(missing cairo/pango) — it must be checked on a machine with those libraries.

### Career Profiling — 🟡 built, needs a functional walkthrough
The n×n mapping-rule grid, band definitions and profiling-solution config are
present (`apps/career_profiling`). Recommend a UI walkthrough against Docs 5 & 6
to confirm it matches the profiling process end-to-end.

### Psychometric Analysis — 🟡 partial
The analysis engine (index computation) and a psychometrician screen with
run-analysis / upload-results exist (`apps/question_bank/psychometrics.py`,
PSY-1/2). **But** the psychometrician's broader module coverage flagged in
Report 4 (Psychometrician Issues 1–5: analysis, QB mgmt, assessment mgmt,
profiling config, report config all "not available") is **not confirmed
complete** and needs a role-by-role check — see Part D.

---

## D. Report 4 — User roles, rights & limits (important, mostly pending)

Report 4 is a large, mostly **separate** body of work: per-role scoping across
12 roles — hiding buttons a role shouldn't see, restricting each role to its own
data (own questions / own courses / own reports), and **corporate org tagging**
(Corp Admin, Group Admin, Corp Exclusive, Channel Partner).

**Honest status:** this was **not** systematically delivered in the completed
scope, with these exceptions that *were* done and are test-backed:

- SME→Reviewer same-domain routing (SME-4 / Reviewer-5) — ✅ `test_reviewer_routing`
- SME task→question autofill via hyperlink (SME-5) — ✅ (UI: Task → "Create question from spec")
- Trainer edit-gating on a published course (Trainer-3/4) — ✅ `test_trainer_cannot_*published*`
- Rich-text on some fields (Trainer-5) — 🟡 partial
- Send Message / Live Chat for all roles — ✅ messaging suite
- Individual pay-before-access gate (Individual-2/13/17) — ✅ `test_priced_assessment_*`
- Invoice create/revise/cancel for empanelled roles — ✅ `test_invoicing`
- Counsellor category tagging, "My Sessions" cleanup, timeslot rules — ❔ needs check

**Everything corporate** (Corp Admin / Group Admin / Corp Exclusive / Channel
Partner org scoping and tagging — the bulk of Report 4) was **explicitly parked
as a separate corporate change-order** and is **not** part of the completed
scope. This needs to be stated plainly to the client.

---

## E. Reports 1–3 (Question types, Training, Counselling)

Large portions here **were** addressed and are traceable to tests (the living
matrix is at `docs/compliance/traceability_matrix.csv`; the signed-vs-built
summary is `docs/compliance/audit_binder.html`). Notable **confirmed** items:
assignment add/edit + report submission + multi-file upload + deadline + trainer
10-point review (Report 3 §3), course structure/sequencing/completion params,
counselling booking/confirmation/refund/followup/feedback, question-scoring
fixes. Recommend the client spot-checks these via the UI and the runner.

---

## F. Suggested agenda for the meeting

1. **Agree the scope split** in writing: (a) SRS + Reports 1–3 items, (b) Report
   4 role-permission scoping, (c) corporate/Corp-Exclusive platform, (d) Report
   5 assessment-parameter items. (b)–(d) were largely outside the completed
   cycle; (c) was already a separate change order.
2. **Two named criticals**: assessment-linking is fixed today; the psychometric
   author flow (Approach 1) needs to be scoped as its own piece.
3. **Run `scripts/verify_client.sh` live** so the client sees exactly which
   items are locked by tests.
4. **Produce a joint line-by-line reconciliation** of Reports 4 & 5 (this guide
   is the honest starting point) so both sides share one done/pending list
   before the testing month.

*This document is intentionally candid. Please review it before sharing; adjust
the framing to suit the commercial conversation.*
