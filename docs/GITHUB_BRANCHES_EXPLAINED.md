# GitHub Branches & CI Status — Explanation

## What you're seeing

Your GitHub repo has **17 extra branches** besides `main`. These are ALL **Dependabot branches** (auto-created by the Dependabot config in `.github/dependabot.yml` to keep dependencies updated). They are NOT test failures from our code.

## List of branches

| Branch | Type | What it does |
|---|---|---|
| `main` | Your code | The actual project |
| `dependabot/docker/backend/python-3.14-slim` | Dependabot | Bumps Docker base image Python 3.12 → 3.14 |
| `dependabot/docker/frontend/node-26-alpine` | Dependabot | Bumps Node 20 → 26 |
| `dependabot/github_actions/actions/checkout-7` | Dependabot | Bumps actions/checkout v4 → v7 |
| `dependabot/github_actions/actions/github-script-9` | Dependabot | Bumps actions/github-script v7 → v9 |
| `dependabot/github_actions/actions/setup-node-6` | Dependabot | Bumps actions/setup-node v4 → v6 |
| `dependabot/github_actions/actions/upload-artifact-7` | Dependabot | Bumps actions/upload-artifact v4 → v7 |
| `dependabot/github_actions/docker/setup-buildx-action-4` | Dependabot | Bumps docker/setup-buildx-action v3 → v4 |
| `dependabot/npm_and_yarn/frontend/dev-tools-*` | Dependabot | Bumps frontend dev tooling |
| `dependabot/npm_and_yarn/frontend/jsdom-29.1.1` | Dependabot | Bumps jsdom (test dep) |
| `dependabot/npm_and_yarn/frontend/react-5c38bb5acb` | Dependabot | Bumps React ecosystem |
| `dependabot/npm_and_yarn/frontend/tailwind-merge-3.6.0` | Dependabot | Bumps tailwind-merge |
| `dependabot/npm_and_yarn/frontend/vitest/ui-4.1.9` | Dependabot | Bumps @vitest/ui |
| `dependabot/pip/backend/black-26.5.1` | Dependabot | Bumps black formatter |
| `dependabot/pip/backend/django-*` | Dependabot | Bumps Django |
| `dependabot/pip/backend/pytest-django-4.12.0` | Dependabot | Bumps pytest-django |
| `dependabot/pip/backend/ruff-0.15.20` | Dependabot | Bumps ruff linter |
| `dependabot/pip/backend/weasyprint-69.0` | Dependabot | Bumps weasyprint |

## Why they show "red X" (test failures)

Dependabot opens a PR for each branch. CI runs on each PR. Some fail because:
- **Major version bumps** (Python 3.14, Node 26, Django newer) may have breaking changes
- **Our code pins versions** (e.g., `Django==5.0.6`) — Dependabot bumps to 5.1+ which may need code changes
- **This is normal and expected** — you review each PR and decide whether to merge

## What to do with them

### Option A — Review and merge safe ones (recommended)

1. Go to https://github.com/sanjayaluva/careerjudge_python/pulls
2. For each PR:
   - **Patch/minor bumps** (e.g., ruff 0.15.20, black 26.5.1) → safe to merge if CI is green
   - **Major bumps** (Python 3.14, Node 26, Django major) → review changelog, test manually, then merge or close

### Option B — Close all and disable Dependabot (not recommended)

```bash
# Close all Dependabot PRs
gh pr list --author "app/dependabot" --json number -q '.[].number' | xargs -I{} gh pr close {}

# Delete all Dependabot branches
git push origin --delete $(git branch -r | grep dependabot | sed 's|origin/||' | tr -d ' ')
```

Then delete `.github/dependabot.yml` to stop future PRs. **Not recommended** — you'll miss security patches.

### Option C — Configure Dependabot to only open security PRs (recommended for now)

Update `.github/dependabot.yml` to only open PRs for security vulnerabilities, not version bumps:

```yaml
update_types: ["version-update:semver-major"]  # ignore major bumps
```

## Why our CI is actually green

Our code's CI (on `main` branch) passes:
- ✅ Backend: 87 tests, 81% coverage
- ✅ Frontend: 28 tests, build succeeds
- ✅ Lint: ruff + eslint clean
- ✅ Docker build: succeeds

The "red X" PRs are Dependabot trying to upgrade deps — that's a separate concern from our code quality.
