# GitHub Actions Secrets Setup

The CI/CD workflows require these secrets to be configured in the GitHub repository:
**Settings → Secrets and variables → Actions → New repository secret**

## Required for CI (already works without these — uses service containers)

None. CI uses GitHub-hosted Postgres service containers.

## Required for CD to Dev

| Secret name | Description | How to generate |
|---|---|---|
| `DEV_SSH_HOST` | Public IP of the dev server | *(your dev server's public IP)* |
| `DEV_SSH_USER` | SSH username on the dev server | `deploy` (create this user) |
| `DEV_SSH_PRIVATE_KEY` | ED25519 private key (PEM format, no passphrase) | `ssh-keygen -t ed25519 -f ~/.ssh/cj_dev_deploy -C "github-actions-deploy@dev"` |

## Required for CD to Prod

| Secret name | Description | How to generate |
|---|---|---|
| `PROD_SSH_HOST` | Public IP of the prod server | *(your prod server's public IP)* |
| `PROD_SSH_USER` | SSH username on the prod server | `deploy` (create this user) |
| `PROD_SSH_PRIVATE_KEY` | ED25519 private key (separate from dev) | `ssh-keygen -t ed25519 -f ~/.ssh/cj_prod_deploy -C "github-actions-deploy@prod"` |
| `PROD_POSTGRES_USER` | Postgres username | `cj` |
| `PROD_POSTGRES_PASSWORD` | Strong Postgres password | `openssl rand -base64 32` |

## How to set up SSH deploy keys

On the dev server:

```bash
# Create deploy user
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG sudo deploy

# Copy your GitHub public key to authorized_keys
sudo mkdir -p /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys

# Allow deploy to run docker without sudo
sudo usermod -aG docker deploy

# Clone the repo
sudo mkdir -p /opt/careerjudge
sudo chown deploy:deploy /opt/careerjudge
sudo -u deploy git clone https://github.com/<org-or-user>/careerjudge_python.git /opt/careerjudge

# Copy env file
sudo -u deploy cp /opt/careerjudge/.env.dev.example /opt/careerjudge/.env.dev
# Edit /opt/careerjudge/.env.dev to set real SECRET_KEY
```

On the GitHub repo:
1. Settings → Secrets and variables → Actions → New repository secret
2. Add `DEV_SSH_HOST` = *(your dev server's public IP)*
3. Add `DEV_SSH_USER` = `deploy`
4. Add `DEV_SSH_PRIVATE_KEY` = contents of `~/.ssh/cj_dev_deploy` (private key)

Repeat for prod server with separate keys.

## Triggering deploys

- **Dev**: push to `main` → auto-deploy via `cd-dev.yml`
- **Prod**: tag a release → auto-deploy via `cd-prod.yml`
  ```bash
  git tag -a v1.0.0 -m "Production release v1.0.0"
  git push origin v1.0.0
  ```

## Manual deploy via Actions UI

- Go to Actions tab → select "Deploy Dev" or "Deploy Prod" workflow
- Click "Run workflow" → select branch/tag → Run
