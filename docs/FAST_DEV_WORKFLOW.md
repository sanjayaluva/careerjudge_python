# Fast Dev Workflow — Skip Docker Rebuilds

> **Problem**: Every code change requires a full Docker image rebuild + container restart via GitHub Actions deploy, which takes 2-3 minutes. This is too slow for iterative development.

> **Solution**: Use volume mounts + hot-reload dev servers so code changes are reflected instantly without rebuilding Docker images.

## Option 1: Local Development (Fastest — No Docker)

Run the backend and frontend directly on your local machine (no Docker, no GCP).

### Backend (Django runserver with auto-reload)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit DATABASE_URL to point to Neon dev DB
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Django's dev server **auto-reloads** on any Python file change — no restart needed. Changes are reflected in <1 second.

### Frontend (Vite dev server with HMR)

```bash
cd frontend
npm install
npm run dev  # starts Vite dev server at http://localhost:5173
```

Vite provides **Hot Module Replacement (HMR)** — React components update instantly in the browser without losing state. Changes are reflected in <500ms.

### Connect frontend to local backend

In `frontend/.env`, set:
```
VITE_API_BASE_URL=http://localhost:8000/api
```

Or use the Vite proxy (already configured in `vite.config.ts`):
```
VITE_API_BASE_URL=/api  # proxies to localhost:8000
```

**This is the fastest workflow — use this for all iterative development.**

---

## Option 2: GCP Dev Server with Volume Mounts (Fast — No Rebuild)

If you need to test on the actual GCP dev server (careerjudge.pp.ua), use a volume-mount docker-compose that skips image rebuilds.

### Create a fast dev compose file

Already created: `infra/docker/docker-compose.dev-fast.yml`

This compose file:
- Mounts the `backend/` and `frontend/` directories as volumes (code changes are live)
- Uses `python manage.py runserver` instead of gunicorn (auto-reload)
- Uses `npm run dev` (Vite HMR) instead of nginx serving static build
- No image rebuild needed — just restart the container

### Usage on GCP server

```bash
# SSH into GCP server
ssh user@35.207.59.232

# Pull latest code
cd /opt/careerjudge
git pull origin main

# Start fast dev mode (no rebuild!)
docker compose -f infra/docker/docker-compose.dev-fast.yml up -d

# Code changes are now live — just `git pull` to update
# Backend auto-reloads on Python file changes
# Frontend Vite HMR updates on React/CSS changes
```

### To update code on GCP:

```bash
# Just pull — no rebuild needed!
git pull origin main

# Backend auto-reloads (runserver watches for file changes)
# Frontend Vite HMR picks up changes automatically
```

---

## Option 3: Docker Rebuild with Layer Caching (Slower but production-like)

The current CI/CD pipeline uses this. Only use when you need to test the actual production Docker image.

### Speed up rebuilds with layer caching

The Dockerfile is already optimized:
1. `requirements.txt` is copied and installed FIRST (before code)
2. Code is copied AFTER pip install
3. So if only code changes (not requirements), the pip install layer is cached

```bash
# Only requirements.txt changes trigger a full rebuild
# Code-only changes reuse the cached pip layer → fast rebuild (~30s)
docker compose -f infra/docker/docker-compose.dev.yml up -d --build backend
```

### GitHub Actions CI/CD (current approach)

- Push to `main` → GitHub Actions SSH deploys to GCP
- Rebuilds Docker image + restarts containers
- Takes 2-3 minutes total

**Use this only for final testing before merging — not for iterative development.**

---

## Recommended Workflow

| Stage | Tool | Speed |
|---|---|---|
| Iterative development (backend) | Local `manage.py runserver` | <1s reload |
| Iterative development (frontend) | Local `npm run dev` (Vite HMR) | <500ms reload |
| Test on GCP dev server | `docker-compose.dev-fast.yml` (volume mounts) | Instant (git pull) |
| Pre-merge / production test | GitHub Actions CI/CD (full rebuild) | 2-3 min |

## Tips for Faster Development

1. **Use local dev for 90% of development** — Django runserver + Vite HMR is 100x faster than Docker rebuilds
2. **Use Neon dev DB** — the same Neon Postgres is accessible from both local and GCP
3. **Only push to main when ready for integration testing** — not for every small change
4. **Use feature branches** — push to a branch, test locally, merge to main when stable
5. **The GCP dev server is for testing the deployed state** — not for iterative development

## Frontend Vite Proxy Setup

The frontend's `vite.config.ts` should have a proxy for `/api` to the backend:

```typescript
export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

This lets you use `VITE_API_BASE_URL=/api` locally without CORS issues.
