#!/usr/bin/env bash
# Deploy script — runs on the dev VM (GCP CE) via SSH from GitHub Actions.
# Pulls latest images, restarts containers, runs migrations.
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/careerjudge}"
COMPOSE_FILE="$DEPLOY_DIR/infra/docker/docker-compose.dev.yml"

cd "$DEPLOY_DIR"

echo "→ Pulling latest code…"
git fetch --all --prune
git reset --hard origin/main

echo "→ Ensuring .env.dev exists…"
if [ ! -f "$DEPLOY_DIR/.env.dev" ]; then
  echo "  .env.dev not found — creating from .env.dev.example"
  cp "$DEPLOY_DIR/.env.dev.example" "$DEPLOY_DIR/.env.dev"
  # Generate a random SECRET_KEY
  NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 50)
  sed -i "s|CHANGE-ME-50-char-random-string-for-dev|$NEW_KEY|" "$DEPLOY_DIR/.env.dev"
  echo "  ✓ .env.dev created with generated SECRET_KEY"
  echo "  ⚠️  Review DATABASE_URL and other settings in .env.dev if needed"
else
  echo "  .env.dev exists — keeping current configuration"
fi

echo "→ Building images…"
docker compose -f "$COMPOSE_FILE" build --pull

echo "→ Starting containers…"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "→ Waiting for backend to be healthy…"
sleep 10

echo "→ Running migrations…"
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py migrate --noinput

echo "→ Skipping collectstatic (not needed in dev — Django serves static files directly)"

echo "→ Health check…"
sleep 5
if curl -fsS http://localhost:8000/api/health/ | grep -q '"status":"ok"'; then
  echo "✓ Deploy successful — backend healthy"
else
  echo "✗ Backend health check failed"
  docker compose -f "$COMPOSE_FILE" logs --tail=50 backend
  exit 1
fi
