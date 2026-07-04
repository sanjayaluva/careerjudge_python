# GitHub Actions — branch protection rules
#
# Apply these via GitHub web UI or API:
#   Repo → Settings → Branches → Branch protection rules
#
# Rule for `main`:
#   - Require pull request before merging
#   - Require status checks to pass:
#       * All CI checks (backend-lint, backend-test, backend-security,
#         frontend-lint, frontend-test, frontend-build, docker-build, ci-pass)
#   - Require branches to be up to date before merging
#   - Do NOT require linear history (we use squash merges)
#   - Require conversation resolution before merging
#   - Restrict who can push to matching branches (admins only)
#
# Rule for `develop`:
#   - Require pull request before merging
#   - Require status checks to pass (same as main)
#   - Allow force pushes (for rebase workflows)
#
# Rule for `v*` tags:
#   - No rule (tags are immutable)
