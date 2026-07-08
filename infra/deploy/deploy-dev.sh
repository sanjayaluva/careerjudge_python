#!/usr/bin/env bash
# Deploy script — runs on the dev VM (GCP CE) via SSH from GitHub Actions.
#
# Uses VOLUME MOUNTS for the backend so code changes are live instantly
# without rebuilding the Docker image. Django runserver auto-reloads on
# Python file changes (<2s).
#
# Frontend is served by Vercel (not on this server) — Caddy proxies /* to Vercel.
#
# First deploy: builds the Docker image (one-time, ~3 min)
# Subsequent deploys: NO rebuild — just restart container with new code (~15s)
# Full rebuild: only when requirements.txt changes or manually triggered
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
  NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 50)
  sed -i "s|CHANGE-ME-50-char-random-string-for-dev|$NEW_KEY|" "$DEPLOY_DIR/.env.dev"
  echo "  ✓ .env.dev created with generated SECRET_KEY"
else
  echo "  .env.dev exists — updating JWT TTLs"
  sed -i 's|^JWT_ACCESS_TTL_MINUTES=.*|JWT_ACCESS_TTL_MINUTES=60|' "$DEPLOY_DIR/.env.dev"
  sed -i 's|^JWT_REFRESH_TTL_DAYS=.*|JWT_REFRESH_TTL_DAYS=30|' "$DEPLOY_DIR/.env.dev"
fi

# Check if we need to rebuild the Docker image.
# Rebuild ONLY if:
# 1. The image doesn't exist yet (first deploy), OR
# 2. requirements.txt changed since last deploy, OR
# 3. FORCE_REBUILD env var is set
NEEDS_REBUILD=false

# Check if the backend image exists (try multiple naming conventions)
BACKEND_IMAGE_EXISTS=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -i "backend" | head -1 || echo "")

if [ -z "$BACKEND_IMAGE_EXISTS" ]; then
  echo "→ No backend Docker image found — need to build (first deploy)"
  NEEDS_REBUILD=true
else
  echo "→ Backend Docker image exists: $BACKEND_IMAGE_EXISTS"

  # Check if requirements.txt changed since last deploy
  REQUIREMENTS_HASH_FILE="$DEPLOY_DIR/.requirements-hash"
  CURRENT_HASH=$(md5sum "$DEPLOY_DIR/backend/requirements.txt" | cut -d' ' -f1)
  SAVED_HASH=$(cat "$REQUIREMENTS_HASH_FILE" 2>/dev/null || echo "")

  if [ "$CURRENT_HASH" != "$SAVED_HASH" ]; then
    echo "→ requirements.txt changed — need to rebuild Docker image"
    NEEDS_REBUILD=true
    echo "$CURRENT_HASH" > "$REQUIREMENTS_HASH_FILE"
  else
    echo "→ requirements.txt unchanged — no rebuild needed"
  fi
fi

if [ "$NEEDS_REBUILD" = "true" ] || [ "${FORCE_REBUILD:-false}" = "true" ]; then
  echo "→ Building Docker image…"
  docker compose -f "$COMPOSE_FILE" build --pull backend
  echo "  ✓ Image built"
else
  echo "→ Skipping Docker rebuild — code changes are live via volume mount"
fi

echo "→ Starting containers (backend + caddy)…"
# Force remove any stale containers from previous deploys (handles name conflicts)
docker rm -f cj-backend-dev cj-backend-fast 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans backend caddy

echo "→ Waiting for backend to be healthy…"
sleep 5

echo "→ Running migrations…"
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py migrate --noinput

echo "→ Health check…"
HEALTH_OK=false
for i in $(seq 1 30); do
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
  echo "✓ Deploy successful — backend healthy (volume mount mode, no rebuild)"
else
  echo "✗ Backend health check failed after 30 attempts"
  echo "  Last response: $RESPONSE"
  docker compose -f "$COMPOSE_FILE" logs --tail=20 backend
  exit 1
fi
