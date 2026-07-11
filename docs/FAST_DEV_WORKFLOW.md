# Development Workflow — Sandbox + Cloud VM

> **Constraint**: Development happens in an agent sandbox environment. There is no local dev server — all testing must be done online via the domain (careerjudge.pp.ua).

## Architecture

```
agent sandbox (code changes)
       ↓ git push to main
       ↓
GitHub Actions CI/CD
       ↓ SSH to dev server
       ↓
Dev cloud VM (backend Docker container)
       ← Caddy reverse proxy →
Frontend CDN (React SPA, auto-builds from main branch)
       ↓
https://careerjudge.pp.ua (online testing)
```

- **Backend**: Cloud VM (Django + gunicorn in Docker)
- **Frontend**: Frontend CDN (React SPA, auto-builds on push to main)
- **Domain**: careerjudge.pp.ua (Caddy reverse proxy with auto-TLS)

## Option 2: Dev VM with Volume Mounts (RECOMMENDED — fastest)

Instead of rebuilding the Docker image on every code change, use **volume mounts** so code changes are live instantly after `git pull` — no rebuild needed.

### How it works

- The `backend/` directory is mounted as a Docker volume → code changes are reflected immediately
- Django's `runserver` (instead of gunicorn) watches for file changes and auto-reloads in <2 seconds
- The `frontend/src` directory is mounted as a volume → Vite HMR picks up changes instantly
- Caddy proxies to the Vite dev server (port 5173) instead of nginx

### Setup (one-time on dev server)

```bash
# SSH into dev server
ssh user@<dev-server-ip>

# Stop the current (rebuild-based) containers
cd /opt/careerjudge
docker compose -f infra/docker/docker-compose.dev.yml down

# Start the fast dev mode (volume mounts, no rebuild)
docker compose -f infra/docker/docker-compose.dev-fast.yml up -d --build
```

This builds the images ONCE (same as before), but then runs with volume mounts + hot-reload.

### Daily development cycle (FAST — no rebuild!)

```bash
# On dev server — just pull, containers auto-reload
cd /opt/careerjudge
git pull origin main

# That's it! Backend auto-reloads in <2s, frontend HMR instant
# Test at https://careerjudge.pp.ua
```

**No `docker compose build` needed!** The volume mount means the container sees the new code immediately. Django's runserver detects file changes and reloads automatically.

### Switching back to production-like mode (for final testing)

```bash
# Stop fast dev mode
docker compose -f infra/docker/docker-compose.dev-fast.yml down

# Start normal (gunicorn + nginx) mode with rebuild
docker compose -f infra/docker/docker-compose.dev.yml up -d --build
```

### Files created for Option 2

- `infra/docker/docker-compose.dev-fast.yml` — volume-mounted dev compose with hot-reload
- `infra/caddy/Caddyfile.dev-fast` — routes to Vite dev server (5173) with WebSocket support for HMR

## Option 3: Docker Rebuild with Layer Caching (fallback)

The current CI/CD pipeline uses this. Use this when you need to test the actual production Docker image (gunicorn + nginx).

### Speed

- Code-only change: ~30s rebuild (pip install layer cached)
- Requirements.txt change: ~2-3 min (full pip reinstall)

### GitHub Actions CI/CD (current approach)

- Push to `main` → GitHub Actions SSH deploys to dev server
- Rebuilds Docker image + restarts containers
- Takes 2-3 minutes total

**Use this for pre-merge integration testing or when Option 2 is not running.**

## Frontend Auto-Deploy

The frontend is deployed separately on a managed frontend CDN:
- The CDN auto-builds the frontend on every push to `main`
- Build takes ~1-2 minutes
- The CDN serves the built SPA globally
- Caddy proxies `/*` to the CDN (browser stays on careerjudge.pp.ua)

**Note**: When using Option 2 (volume mounts), the frontend runs on the dev server via Vite dev server instead. Caddy routes to `frontend:5173`. This gives instant HMR but is dev-only — production still uses the managed CDN.

## When to Do a Full/Complete Rebuild

A full rebuild (no layer caching) is only needed:
- When `requirements.txt` changes (new Python packages)
- When the Dockerfile itself changes
- At project finalization (handing over to client)
- When changing deployment target (different domain, different server)

```bash
# Full clean rebuild (no cache)
docker compose -f infra/docker/docker-compose.dev.yml build --no-cache
docker compose -f infra/docker/docker-compose.dev.yml up -d
```

This takes 5-10 minutes but only needs to be done once at delivery time.

## Summary

| Option | Speed | When to use |
|---|---|---|
| **Option 2: Volume mounts** | Instant (git pull) | **Daily iterative dev (recommended)** |
| Option 3: Cached rebuild | ~30s-2min | Pre-merge / production-like testing |
| Full rebuild (no cache) | ~5-10 min | Project finalization / client handover |

**Recommended**: Use Option 2 for daily development. Switch to Option 3 for final testing before client handover.
