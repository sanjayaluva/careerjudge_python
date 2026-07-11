# Backend Auto-Deploy Setup

A managed frontend CDN auto-deploys the frontend on every push to `main`. This guide sets up the same for the backend — every push to `main` auto-deploys to the dev server via GitHub Actions SSH.

## Architecture

```
git push to main
      │
      ▼
┌─────────────────────────────────────────┐
│  GitHub Actions (cd-dev.yml workflow)   │
│  1. Checkout code                       │
│  2. SSH into dev server                 │
│  3. Run deploy-dev.sh:                  │
│     - git pull                          │
│     - docker compose build              │
│     - docker compose up -d              │
│     - python manage.py migrate          │
│     - health check                      │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│  Dev cloud VM (careerjudge.pp.ua)       │
│  - Backend container (restarted)        │
│  - Caddy container (reloaded)           │
│  - Postgres DB (migrated)               │
└─────────────────────────────────────────┘
```

## Step 1 — Create a deploy SSH key (on your local machine)

```bash
# Generate a dedicated ED25519 key for GitHub Actions (no passphrase)
ssh-keygen -t ed25519 -f ~/.ssh/cj_dev_deploy -C "github-actions-deploy@dev"
# Press Enter for no passphrase

# This creates:
#   ~/.ssh/cj_dev_deploy      (private key — goes in GitHub secrets)
#   ~/.ssh/cj_dev_deploy.pub  (public key — goes on the dev server)
```

## Step 2 — Add the public key to the dev server

```bash
# From your local machine — copy the public key to the dev server
ssh-copy-id -i ~/.ssh/cj_dev_deploy.pub <deploy-user>@<dev-server-ip>

# OR manually — append to the server's authorized_keys:
cat ~/.ssh/cj_dev_deploy.pub | ssh <deploy-user>@<dev-server-ip> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Test that the key works (should login without password):
ssh -i ~/.ssh/cj_dev_deploy <deploy-user>@<dev-server-ip> "echo 'SSH key works!'"
```

> Replace `<deploy-user>` with the SSH user on the dev server and `<dev-server-ip>` with the dev server's public IP.

## Step 3 — Add GitHub Actions secrets

Go to: `https://github.com/<org-or-user>/careerjudge_python/settings/secrets/actions`

Click **"New repository secret"** for each:

| Secret name | Value |
|---|---|
| `DEV_SSH_HOST` | *(dev server public IP)* |
| `DEV_SSH_USER` | *(deploy user on the dev server)* |
| `DEV_SSH_PRIVATE_KEY` | *(paste the entire contents of `~/.ssh/cj_dev_deploy` — the private key, starting with `-----BEGIN OPENSSH PRIVATE KEY-----` and ending with `-----END OPENSSH PRIVATE KEY-----`)* |

To get the private key contents:
```bash
cat ~/.ssh/cj_dev_deploy
# Copy the ENTIRE output including the BEGIN/END lines
```

## Step 4 — Ensure the deploy script exists on the dev server

The deploy script (`infra/deploy/deploy-dev.sh`) is already in the repo. It:
1. `git pull origin main`
2. `docker compose build backend`
3. `docker compose up -d backend caddy`
4. `python manage.py migrate`
5. `python manage.py collectstatic`
6. Health check via `curl /api/health/`

The GitHub Actions workflow (`cd-dev.yml`) SSHes in and runs this script.

## Step 5 — Test the auto-deploy

1. Make a small change (e.g., update README)
2. Commit and push to `main`:
   ```bash
   git add README.md
   git commit -m "docs: test auto-deploy"
   git push origin main
   ```
3. Go to `https://github.com/<org-or-user>/careerjudge_python/actions`
4. You should see "Deploy Dev" workflow running
5. After ~1-2 minutes, it should show ✓ green
6. Verify the backend is still healthy:
   ```bash
   curl https://careerjudge.pp.ua/api/health/
   # Should return {"status":"ok"}
   ```

## How it works

The workflow file (`.github/workflows/cd-dev.yml`):

```yaml
on:
  push:
    branches: [main]  # triggers on every push to main

jobs:
  deploy:
    steps:
      - uses: actions/checkout@v4
      - name: Setup SSH
        run: |
          echo "${{ secrets.DEV_SSH_PRIVATE_KEY }}" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H ${{ secrets.DEV_SSH_HOST }} >> ~/.ssh/known_hosts
      - name: Run deploy script
        run: |
          ssh ${{ secrets.DEV_SSH_USER }}@${{ secrets.DEV_SSH_HOST }} \
            "cd /opt/careerjudge && bash infra/deploy/deploy-dev.sh"
```

## Troubleshooting

### "Permission denied (publickey)"

- The SSH key wasn't added to the dev server correctly
- Re-run: `ssh-copy-id -i ~/.ssh/cj_dev_deploy.pub <deploy-user>@<dev-server-ip>`
- Verify: `ssh -i ~/.ssh/cj_dev_deploy <deploy-user>@<dev-server-ip> "whoami"`

### "Host key verification failed"

- The server's host key isn't in `known_hosts`
- The workflow runs `ssh-keyscan` automatically, but if the server was recreated, the key changed
- Fix: add `StrictHostKeyChecking=accept-new` to the SSH command in the workflow

### Deploy succeeds but backend is down

- Check server logs: `docker compose -f /opt/careerjudge/infra/docker/docker-compose.dev.yml logs --tail=50 backend`
- Common cause: migration failed (DB issue) → check migration output in the Actions log

### "docker: command not found" on SSH

- The deploy user isn't in the `docker` group
- Fix on server: `sudo usermod -aG docker <deploy-user> && newgrp docker`

## Production auto-deploy

Same setup but with separate secrets:

| Secret | Value |
|---|---|
| `PROD_SSH_HOST` | *(prod server public IP)* |
| `PROD_SSH_USER` | *(deploy user on the prod server)* |
| `PROD_SSH_PRIVATE_KEY` | *(separate ED25519 key for prod)* |
| `PROD_POSTGRES_USER` | `cj` |
| `PROD_POSTGRES_PASSWORD` | *(strong password)* |

The `cd-prod.yml` workflow triggers on **tags** (`v*.*.*`), not pushes to `main`:

```bash
# Create a production release
git tag -a v1.0.0 -m "Production release v1.0.0"
git push origin v1.0.0
# This triggers cd-prod.yml → deploys to prod server with DB backup
```

## Summary

| Trigger | Frontend (CDN) | Backend (dev server) | Backend (prod server) |
|---|---|---|---|
| Push to `main` | ✅ Auto-deploys | ✅ Auto-deploys (after secrets set) | ❌ |
| Push tag `v*.*.*` | ✅ Auto-deploys | ✅ Auto-deploys | ✅ Auto-deploys (after secrets set) |
| Pull request | ✅ Preview deploy | ❌ CI runs only | ❌ CI runs only |

Once you set up the 3 GitHub secrets (`DEV_SSH_HOST`, `DEV_SSH_USER`, `DEV_SSH_PRIVATE_KEY`), every `git push origin main` will auto-deploy both frontend (CDN) and backend (dev server) simultaneously.
