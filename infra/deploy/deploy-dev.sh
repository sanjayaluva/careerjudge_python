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

echo "→ Building images…"
docker compose -f "$COMPOSE_FILE" build --pull

echo "→ Starting containers…"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "→ Running migrations…"
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py migrate --noinput

echo "→ Collecting static files…"
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py collectstatic --noinput

echo "→ Health check…"
sleep 5
if curl -fsS http://localhost:8000/api/health/ | grep -q '"status":"ok"'; then
  echo "✓ Deploy successful — backend healthy"
else
  echo "✗ Backend health check failed"
  docker compose -f "$COMPOSE_FILE" logs --tail=50 backend
  exit 1
fi
