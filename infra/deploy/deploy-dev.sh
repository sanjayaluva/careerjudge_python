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
# Subsequent deploys: NO rebuild — just restart container with new code (~10s)
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/careerjudge}"
COMPOSE_FILE="$DEPLOY_DIR/infra/docker/docker-compose.dev.yml"
FAST_COMPOSE_FILE="$DEPLOY_DIR/infra/docker/docker-compose.dev-fast.yml"

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

# Check if the backend Docker image already exists
# If it does, skip the rebuild — volume mounts make code changes live
BACKEND_IMAGE=$(docker images --format '{{.Repository}}' | grep "docker-backend" || echo "")

if [ -z "$BACKEND_IMAGE" ]; then
  echo "→ First deploy: building Docker image (one-time, ~3 min)…"
  docker compose -f "$COMPOSE_FILE" build --pull backend
  echo "  ✓ Image built — future deploys will skip this step"
else
  echo "→ Docker image exists — skipping rebuild (volume mounts make code live)"
fi

echo "→ Starting backend container with volume mount (auto-reload)…"
# Stop old containers (both normal and fast names)
docker rm -f cj-backend-dev cj-backend-fast 2>/dev/null || true

# Start backend with volume mount + runserver (auto-reload)
# We use the dev.yml compose for the image but override the command + add volume mount
docker compose -f "$COMPOSE_FILE" run -d \
  --name cj-backend-dev \
  --service-ports \
  --no-deps \
  -v "$DEPLOY_DIR/backend:/app" \
  -e DJANGO_SETTINGS_MODULE=config.settings.dev \
  --entrypoint "" \
  backend \
  python manage.py runserver 0.0.0.0:8000

echo "→ Ensuring Caddy is running…"
docker compose -f "$COMPOSE_FILE" up -d caddy

echo "→ Waiting for backend to be healthy…"
sleep 5

echo "→ Running migrations…"
docker exec cj-backend-dev python manage.py migrate --noinput

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
  docker logs --tail=20 cj-backend-dev
  exit 1
fi
