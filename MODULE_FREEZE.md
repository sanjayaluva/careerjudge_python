# Module Freeze Log

This document tracks which modules are frozen (additive-only) and their current version.

| Module | Frozen Since | Current Version | Notes |
|---|---|---|---|
| accounts | 2026-07-01 | v1.1.0 | Phase 1 complete + additive updates (bulk upload, channel_partner, profile fields, scoped deletion) |
| organizations | 2026-07-02 | v1.0.0 | Phase 2 — multi-tenancy foundation (org CRUD, groups, members) |
| question_bank | — | (not frozen) | Phase 2 — backend + frontend complete, pending freeze |
| assessment | — | (not frozen) | Phase 2 — pending |
| career_profiling | — | (not frozen) | Phase 3 |
| reporting | — | (not frozen) | Phase 3 |
| training | — | (not frozen) | Phase 4 |
| counseling | — | (not frozen) | Phase 4 |
| cms | — | (not frozen) | Phase 4 |
| notifications | — | (not frozen) | Phase 1 (minimal) → Phase 4 (full) |

## v1.1.0 Additive Changes (on top of v1.0.0)

- Role-specific profile fields per SRS pages 8-22 (individual, professional, channel partner)
- Bulk user upload (CSV) per SRS page 18 + admin spec 2.3
- Channel Partner as 11th system role per admin spec 2.1
- Scoped individual user deletion (CJ Admin: any; org admins: within org only)
- Improved error messages with field-specific details
- Trailing slash fixes on all API endpoints
- JWT sliding session (60 min access, 30 day refresh)
- Organizations module (multi-tenancy foundation)

## Freeze policy

A module becomes **frozen** when:

1. Its first version tag (`vX.Y.0`) is pushed
2. It has been deployed to prod
3. It has ≥80% test coverage
4. It is documented in `docs/modules/<name>.md`

Once frozen, the module accepts **additive changes only**:

- ✅ New endpoints (under new URL paths)
- ✅ New nullable model fields (via additive migration)
- ✅ New permissions
- ✅ New optional query/body parameters
- ✅ New optional response fields
- ❌ Removing or renaming endpoints
- ❌ Changing response schemas
- ❌ Removing or renaming model fields
- ❌ Changing permission semantics

Breaking changes require a **new versioned module** (e.g. `assessment_v2/`) and a documented deprecation path.

## Commit footer

Every commit touching a module must include:

```
MODULE-FREEZE: <module-name> (vX.Y.Z) — additive only
```

or for unfrozen modules:

```
MODULE-FREEZE: none (<module-name> not yet frozen)
```
