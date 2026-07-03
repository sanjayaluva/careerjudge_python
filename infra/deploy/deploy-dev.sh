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
  echo "  .env.dev exists — updating JWT TTLs to prevent mid-session expiry"
  # Force-update JWT TTLs to the latest values (60 min access, 30 day refresh).
  # Previous deploys used 15 min / 7 days which caused session_expired redirects
  # during active question editing. This sed is idempotent — safe to run every deploy.
  sed -i 's|^JWT_ACCESS_TTL_MINUTES=.*|JWT_ACCESS_TTL_MINUTES=60|' "$DEPLOY_DIR/.env.dev"
  sed -i 's|^JWT_REFRESH_TTL_DAYS=.*|JWT_REFRESH_TTL_DAYS=30|' "$DEPLOY_DIR/.env.dev"
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
# Wait for backend to be ready (retry up to 30 times = 60 seconds)
# Use a simple approach: curl the health endpoint and check if response contains "ok"
HEALTH_OK=false
for i in $(seq 1 30); do
  # curl -s: silent, -S: show errors, --max-time 5: don't hang
  RESPONSE=$(curl -s --max-time 5 http://localhost:8000/api/health/ 2>&1 || echo "CURL_FAILED")
  if [ "$RESPONSE" != "CURL_FAILED" ] && echo "$RESPONSE" | grep -q "ok"; then
    HEALTH_OK=true
    echo "  ✓ Backend healthy (attempt $i): $RESPONSE"
    break
  fi
  echo "  Waiting for backend… (attempt $i/30) — last response: $RESPONSE"
  sleep 2
done

if [ "$HEALTH_OK" = "true" ]; then
  echo "✓ Deploy successful — backend healthy"
else
  echo "✗ Backend health check failed after 30 attempts"
  echo "  Last response: $RESPONSE"
  docker compose -f "$COMPOSE_FILE" logs --tail=20 backend
  exit 1
fi
