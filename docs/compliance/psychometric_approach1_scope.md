# Scope & Estimate — Psychometric "Approach 1" Author Flow

*Report 5 → Assessment Parameter Setting → §3 Issue 5. The client's #1 named
critical. This is a SIGNED requirement (Doc 1 §3.1.6, Doc 1.1 §6a/§8a, Doc 3
§4.1/§4.2.2/§4.2.3), now under remediation.*

> **Status: PARTIALLY REMEDIATED.**
> **Done & tested:** the signed **authoring** flow (a `PSYCHOMETRIC_STATEMENT`
> question type — bare statement, no options; validator + QB editor support) and
> the **configuration** flow (`PsychometricGroup`/`PsychometricGroupItem` models,
> `/assessments/<id>/psychometric-groups/` API with the grouping rules enforced,
> and a "Psychometric Groups" config tab). A psychometrician can now author
> statements and build Rank Groups / Forced-Choice Pairs — the exact flow the
> client asked for, replacing the error-prone Approach-2 option-tagging.
> **Remaining:** delivering those groups to the candidate in the session player
> and scoring from the groups (session-engine integration) — see §3.4 below.

---

## 1. What the client asked for (Approach 1)

Psychometric **statements** are authored **in the Question Bank first** — one
statement per question, **no options** — under the psychometric
categories/subcategories. Each statement gets a code (e.g. `C1S1Q1`). Because
they are ordinary Question-Bank questions, **SMEs can create them and Reviewers
can review them**.

Then, at **assessment configuration** time, the psychometrician:

1. **Assigns statements to sections.** The section is the statement's
   Question-Bank category — so there is nothing to hand-tag; it is derived.
2. **Groups statements** into the delivery unit for the question type:
   - **Rank types** (`RANK_SIMPLE`, `RANK_THEN_RATE`) → **Rank Groups**.
     Rule: *number of sections = number of rank options*, and *each rank group
     holds one — and only one — statement from each section*.
   - **Forced-Choice types** (`FORCED_CHOICE_SINGLE_LEVEL`, `…_TWO_LEVEL`) →
     **FC Pairs**. Rule: *the two statements in a pair come from two different
     L1 sections* (never the same section).

Why the client wants this: tagging happens once, at authoring time, so the
error-prone back-tagging step disappears, and the work can be split across SME /
Reviewer / Psychometrician instead of one person doing everything.

## 2. What exists today (Approach 2 — the deprecated one)

- A single Rank/FC **Question** holds N **ResponseOptions**, and each option
  carries a free-text `section_tag` (`apps/question_bank/models.py`
  `ResponseOption.section_tag`).
- At assignment, `_ensure_section_tags_have_sections`
  (`apps/assessment/views.py`) back-creates an `AssessmentSection` per distinct
  tag.
- Scoring reads each option's `section_tag` → (raw, max)
  (`apps/assessment/scoring.py`, `score_psychometric_option_groups`).

This is exactly the flow the client flagged as error-prone and single-user. It
works, but it is not Approach 1.

## 3. Target design

### 3.1 Data model
- **Statement questions**: reuse the Question model with a new lightweight type
  (e.g. `PSYCHOMETRIC_STATEMENT`) — one statement in `question_text_1`, no
  options, category = its section/domain. SME/Reviewer workflow already applies.
- **Grouping at assessment level** — new models:
  - `PsychometricGroup(assessment_section OR assessment, group_type=rank|fc,
    group_number, rate_scale?)`
  - `PsychometricGroupItem(group, question[statement], role/slot)` — the N
    statements in a Rank Group (one per section) or the 2 in an FC Pair.
- Section is read from each statement's category (no `section_tag`).

### 3.2 Authoring (SME) — small
Statement questions are ordinary QB questions; the editor needs a "statement"
mode (hide the options UI). Reviewer/psychometrician review flow is unchanged.

### 3.3 Assessment configuration (Psychometrician) — the bulk of the work
A new configuration UI:
- pick statements (filtered by category/section);
- auto-place each under its section;
- build Rank Groups / FC Pairs with **live validation** of the two rules above
  (one-per-section for rank; two-different-sections for FC);
- persist as `PsychometricGroup` + items.

### 3.4 Player & scoring
- Player renders each Rank Group / FC Pair from its grouped statements (instead
  of one question's option list).
- Scoring reads statement→section from the group items (adapt
  `score_psychometric_option_groups` to consume groups; keep the old path for
  legacy Approach-2 assessments).

### 3.5 Migration / back-compat
Existing Approach-2 assessments keep working (old scoring path stays). New
assessments use Approach 1. Optionally a one-off converter later.

## 4. Work breakdown & rough estimate

| Piece | Effort (dev-days) |
|---|---|
| Statement question type + editor mode + validation | 1.5 |
| `PsychometricGroup` / `PsychometricGroupItem` models + migration + serializers | 1.5 |
| Assessment-config grouping UI (rank groups + FC pairs, live rule validation) | 3–4 |
| Player rendering from groups (rank + FC, single/two-level) | 2 |
| Scoring adapted to group items (+ keep legacy path) | 1.5 |
| Tests (author → configure → deliver → score, both rules) | 1.5 |
| **Total** | **≈ 11–12 dev-days** |

This is a **feature build**, not a patch — which is why it could not be closed
in the current pass and is called out separately. (Rough token budget if built
here in the same style as the rest of the work: ~20–25M tokens.)

## 5. Open questions to confirm with the client
1. `RANK_THEN_RATE` and `FORCED_CHOICE_TWO_LEVEL` — confirm the rating/second-
   level still attaches per statement in the new flow.
2. Should existing Approach-2 assessments be **migrated**, or only new ones use
   Approach 1?
3. For FC "two different L1 sections" — confirm whether subsections of the same
   L1 count as the same section (the diagram implies L1-level grouping).

## 6. Recommendation
Approve this as a discrete work item before the testing month. It is
self-contained, testable end-to-end, and removes the client's single biggest
correctness concern.
