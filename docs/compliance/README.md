# Compliance Traceability Matrix

`traceability_matrix.csv` is the living record of **what was signed vs. what was built** for the
Career Judge dossier-completion build (Path 2 — wishlist + modified-list). It is the spine of the
audit binder produced at milestone M7.

Seeded 18 Sep 2026 from the SRS-trace certification (`../../career_judge_srs_trace_certification_2026-09-18.html`)
and the M0 feedback-report sweep.

## Columns

- **clause_id** — stable ID. Reference it in commit messages that implement or change a row
  (e.g. `feat(ASM-1): delivery-count author UI`).
- **requirement** — one-line statement of the obligation.
- **source_doc** — the signed clause it traces to, or `none` for elective/no-basis items.
- **category**:
  - `SIGNED-DONE` — signed requirement, already implemented & tested.
  - `SIGNED-PARTIAL` — signed, partly implemented (completion tracked to a milestone).
  - `SIGNED-PENDING` — signed requirement, not yet built; assigned to a milestone.
  - `FEEDBACK-R2` / `FEEDBACK-R3` — built updates driven by testing-feedback Report 2 / Report 3.
    **These are intentional updates and are PRESERVED** — they are not contradictions and must not
    be reverted. Labelled here so the binder distinguishes signed obligations from feedback work.
  - `ELECTIVE` — no signed basis; built only by wishlist / extra-scope election (M6 / M6B).
    Additive; excluding any of these does not affect the signed-vs-built audit.
- **status** — done / partial / pending / backlog.
- **milestone** — M0–M7 where pending/backlog work lands.
- **implementing_files**, **covering_tests** — evidence. Firmed up as each milestone touches the code.
- **notes** — trims, caveats, reconciliation decisions.

## Audit rule

The build **survives a signed-vs-built audit** when every `SIGNED-*` row is `done` with an
implementing file and a passing test. `FEEDBACK-*` and `ELECTIVE` rows are additive and never
cause an audit failure. The signed-complete set closes at **M5**.

## Corporate line (excluded)

Extra-scope items 1 & 2 (multi-tenant orgs & groups control system; Corporate-Exclusive platform,
CJ_UC052–055) are **out of this build** — a separate, separately-priced change order. They are not
rows in this matrix.
