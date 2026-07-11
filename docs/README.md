# CareerJudge Documentation

This folder contains all project documentation. The [root README.md](../README.md) has the quick-start guide and basic project info.

## Table of Contents

### Project Overview
- [PROJECT_STATUS.md](PROJECT_STATUS.md) — Current development status, completed modules, next priorities
- [ARCHITECTURE_PLAN.md](ARCHITECTURE_PLAN.md) — Overall architecture and phased development plan
- [GAP_ANALYSIS.md](GAP_ANALYSIS.md) — Gap analysis vs SRS spec
- [PHASE2_PLAN.md](PHASE2_PLAN.md) — Phase 2 detailed plan (organizations + question_bank + assessment)

### Development
- [CONTRIBUTING.md](CONTRIBUTING.md) — Coding standards, git workflow, PR process
- [MODULE_FREEZE.md](MODULE_FREEZE.md) — Module freeze policy (additive-only changes after version tag)
- [FAST_DEV_WORKFLOW.md](FAST_DEV_WORKFLOW.md) — Volume-mount fast deploy workflow (~15s code-only redeploy)

### Infrastructure & Deployment
- [ACTIONS_SECRETS_SETUP.md](ACTIONS_SECRETS_SETUP.md) — GitHub Actions secrets configuration
- [BRANCH_PROTECTION.md](BRANCH_PROTECTION.md) — Branch protection rules
- [BACKEND_AUTODEPLOY.md](BACKEND_AUTODEPLOY.md) — Backend auto-deploy via GitHub Actions SSH
- [GITHUB_BRANCHES_EXPLAINED.md](GITHUB_BRANCHES_EXPLAINED.md) — Branch strategy explanation

### Module Documentation

Each module has its own doc in [modules/](modules/):

| Module | Version | Status | Tests | Doc |
|---|---|---|---|---|
| Accounts | v1.1.0 | ✅ Frozen | 83 tests, 84% coverage | [accounts.md](modules/accounts.md) |
| Organizations | v1.0.0 | ✅ Frozen | 82% coverage | [organizations.md](modules/organizations.md) |
| Question Bank | v1.0.0-pre | 🔧 Active | 53 tests | [question_bank.md](modules/question_bank.md) |
| Assessment | v1.0.0-pre | 🔧 Active | 76 tests | [assessment.md](modules/assessment.md) |
| Career Profiling | — | 📋 Planned | — | — |
| Reporting | — | 📋 Planned | — | — |
| Training | — | 📋 Planned | — | — |
| Counseling | — | 📋 Planned | — | — |
| CMS | — | 📋 Planned | — | — |
| Notifications | — | 📋 Planned | — | — |

### Documentation Conventions

- **Module docs** are created in `modules/<module_name>.md` AFTER the module development finalizes (or when frozen).
- **Update module docs** when adding new features, endpoints, or changing behavior — keep docs in sync with code.
- **README.md** at the repo root is the only doc that stays outside `docs/` — it's the entry point with quick-start info.
- All other documentation (guides, plans, module specs, infra setup) lives in this `docs/` folder.

### Future Module Documentation Template

When starting a new module, create `docs/modules/<module_name>.md` using this structure:

```markdown
# <Module Name> — <version> (<status>)

> **Frozen since**: <date or "not yet">
> **Version**: <version>
> **Phase**: <phase number>
> **Test coverage**: <count> tests, <%> coverage

## Overview
<what the module does>

## Public API
<endpoint table>

## Models
<model descriptions>

## Frontend
<page descriptions>

## Permissions
<role × action matrix>

## Frozen contract (if frozen)
<what cannot change>
```
