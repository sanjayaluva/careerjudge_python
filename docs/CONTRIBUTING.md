# Contributing to CareerJudge

## 1. Branch model

```
main (protected, deployable to prod)
  └─ develop (integration branch, deployable to dev)
       └─ feature/<module>-<scope>
       └─ fix/<module>-<scope>
       └─ chore/<module>-<scope>
       └─ docs/<scope>
```

- `main` only receives merges from `develop` via PR with green CI.
- `develop` receives merges from feature/fix/chore branches via PR.
- For Phase 1 (initial build), we push directly to `main` with disciplined commits; once Phase 1 ships, switch to `develop` integration.

## 2. Commit convention — Conventional Commits

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | When to use |
|---|---|
| `feat` | New feature (user-visible) |
| `fix` | Bug fix (user-visible) |
| `test` | Adding or improving tests only |
| `ci` | CI/CD config changes |
| `docs` | Documentation only |
| `refactor` | Code restructuring without behavior change |
| `chore` | Tooling, deps, config |
| `perf` | Performance improvement |
| `build` | Build system / Docker / deps |

### Scopes

Use the module name: `accounts`, `organizations`, `question_bank`, `assessment`, `career_profiling`, `reporting`, `training`, `counseling`, `cms`, `notifications`, `infra`, `ci`, `core`, `frontend`.

### Examples

```
feat(accounts): add JWT login endpoint with refresh rotation

Implements POST /api/auth/login returning access + refresh tokens.
Refresh tokens rotate on use; blacklisted on logout.

MODULE-FREEZE: none (initial)
```

```
feat(question_bank): add tag field to Question (additive)

MODULE-FREEZE: question_bank (v1.2.0) — additive only
```

## 3. Module freeze policy

See [`MODULE_FREEZE.md`](./MODULE_FREEZE.md) for the live freeze log.

### Rules

- A module becomes frozen when its first version (`vX.Y.0`) is tagged and deployed to prod.
- **Allowed on frozen modules** (additive only):
  - New API endpoints
  - New nullable model fields (with migration)
  - New permissions
  - New optional query parameters
  - New optional request body fields
- **Forbidden on frozen modules**:
  - Removing or renaming existing endpoints
  - Changing response schemas
  - Removing or renaming model fields
  - Changing permission semantics
  - Breaking changes to request validation
- **Breaking changes** require a new versioned module (e.g. `assessment_v2/`) with a documented deprecation path.

### Commit footer

Every commit touching a module must include a footer indicating freeze status:

```
MODULE-FREEZE: <module-name> (vX.Y.Z) — additive only
```

or for unfrozen modules:

```
MODULE-FREEZE: none (<module-name> not yet frozen)
```

CI will reject commits missing this footer on module code paths.

## 4. Testing standards

### Coverage requirements

- **Backend**: ≥80% line coverage on touched files (enforced by CI)
- **Frontend**: ≥80% line coverage on touched files (enforced by CI)
- Every API endpoint must have at minimum:
  - 1 happy-path test
  - 1 authentication failure test (401/403)
  - 1 validation failure test (400)
  - 1 not-found test where applicable (404)

### Backend tests

```python
# backend/apps/accounts/tests/test_views.py
import pytest
from rest_framework.test import APIClient
from .factories import UserFactory

@pytest.mark.django_db
class TestLoginEndpoint:
    def test_happy_path(self, client):
        user = UserFactory(email="test@example.com", password="Pass1234!")
        resp = client.post("/api/auth/login", {"email": user.email, "password": "Pass1234!"})
        assert resp.status_code == 200
        assert "access" in resp.json()

    def test_invalid_credentials(self, client):
        resp = client.post("/api/auth/login", {"email": "nope@x.com", "password": "x"})
        assert resp.status_code == 401
```

### Frontend tests

```typescript
// frontend/src/pages/auth/LoginPage.test.tsx
import { render, screen } from "@testing-library/react";
import { LoginPage } from "./LoginPage";

test("renders email and password fields", () => {
  render(<LoginPage />);
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
});
```

### E2E tests (Playwright)

Every use case should have at least one E2E test in `frontend/e2e/`:

```
frontend/e2e/
├── auth-login.spec.ts
├── auth-signup.spec.ts
├── auth-email-verify.spec.ts
├── auth-password-reset.spec.ts
└── admin-users-crud.spec.ts
```

## 5. Code quality

### Backend

- `ruff check backend/` — lint
- `black --check backend/` — format
- `mypy backend/` — types
- `bandit -r backend/` — security
- `pip-audit` — dependency vulnerabilities

### Frontend

- `eslint frontend/` — lint
- `tsc --noEmit` — types
- `prettier --check frontend/` — format
- `npm audit` — dependency vulnerabilities

## 6. PR checklist

Before requesting review:

- [ ] Branch name follows convention
- [ ] Commits follow Conventional Commits with MODULE-FREEZE footer
- [ ] CI is green (lint, test, build, security)
- [ ] Coverage ≥80% on touched files
- [ ] No secrets committed
- [ ] If touching a frozen module: changes are strictly additive
- [ ] If adding migrations: tested both forward and backward
- [ ] If adding env vars: documented in `.env.example`
- [ ] If adding endpoints: documented in OpenAPI schema
- [ ] If adding frontend routes: role-based access checked

## 7. Secrets handling

- **Never** commit secrets to git.
- All secrets via environment variables.
- Local dev: copy `.env.example` to `.env`, fill in values.
- CI/CD: GitHub Actions secrets (encrypted).
- Prod: OCI/GCP secret managers or `.env` files with `chmod 600` owned by deploy user only.

## 8. Reviewer guidelines

- Reject PRs that touch frozen modules with non-additive changes.
- Reject PRs missing tests.
- Reject PRs with secrets.
- Reject PRs with `# noqa` or `@ts-ignore` without justification comments.
- Request changes if coverage <80% on touched files.
- Approve only when CI is green and checklist is complete.
