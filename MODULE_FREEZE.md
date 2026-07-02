# Module Freeze Log

This document tracks which modules are frozen (additive-only) and their current version.

| Module | Frozen Since | Current Version | Notes |
|---|---|---|---|
| accounts | 2026-07-01 | v1.0.0 | Phase 1 complete — auth, RBAC, profile, demo seeder |
| organizations | — | (not frozen) | Phase 2 |
| question_bank | — | (not frozen) | Phase 2 |
| assessment | — | (not frozen) | Phase 2 |
| career_profiling | — | (not frozen) | Phase 3 |
| reporting | — | (not frozen) | Phase 3 |
| training | — | (not frozen) | Phase 4 |
| counseling | — | (not frozen) | Phase 4 |
| cms | — | (not frozen) | Phase 4 |
| notifications | — | (not frozen) | Phase 1 (minimal) → Phase 4 (full) |

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
