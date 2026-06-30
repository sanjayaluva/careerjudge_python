#!/usr/bin/env bash
# Deploy script — runs on the prod VM (OCI Ampere A1) via SSH from GitHub Actions.
# Pulls latest images, restarts containers, runs migrations with backup.
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/careerjudge}"
COMPOSE_FILE="$DEPLOY_DIR/infra/docker/docker-compose.prod.yml"

cd "$DEPLOY_DIR"

echo "→ Pulling latest code (tag $GIT_TAG)…"
git fetch --all --tags --prune
git reset --hard "$GIT_TAG"

echo "→ Backing up database…"
docker compose -f "$COMPOSE_FILE" exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "/opt/backups/cj-$(date +%Y%m%d-%H%M%S).sql.gz"

echo "→ Building images…"
docker compose -f "$COMPOSE_FILE" build --pull

echo "→ Starting containers…"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "→ Running migrations…"
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py migrate --noinput

echo "→ Collecting static files…"
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py collectstatic --noinput

echo "→ Health check…"
sleep 10
if curl -fsS http://localhost:8000/api/health/ | grep -q '"status":"ok"'; then
  echo "✓ Production deploy successful — backend healthy"
else
  echo "✗ Backend health check failed — rolling back"
  docker compose -f "$COMPOSE_FILE" logs --tail=100 backend
  # Note: rollback is manual via git reset --hard <previous-tag>
  exit 1
fi
