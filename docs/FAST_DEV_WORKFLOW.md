# Development Workflow — z.ai Sandbox + GCP + Vercel

> **Constraint**: Development happens in the z.ai agent sandbox environment. There is no local dev server — all testing must be done online via the domain (careerjudge.pp.ua).

## Architecture

```
z.ai sandbox (code changes)
       ↓ git push to main
       ↓
GitHub Actions CI/CD
       ↓ SSH to GCP
       ↓
GCP Compute Engine (backend Docker container)
       ← Caddy reverse proxy →
Vercel (frontend CDN, builds from main branch)
       ↓
https://careerjudge.pp.ua (online testing)
```

- **Backend**: GCP Compute Engine (Django + gunicorn in Docker)
- **Frontend**: Vercel (React SPA, auto-builds on push to main)
- **Domain**: careerjudge.pp.ua (Caddy reverse proxy with auto-TLS)

## Deployment Speed

### Current: Docker Rebuild with Layer Caching (~30s for code-only changes)

The Dockerfile is optimized with layer caching:
1. `requirements.txt` is copied and installed FIRST (cached layer)
2. Code is copied AFTER pip install
3. If only code changes (not requirements), the pip install layer is reused

**Code-only change**: ~30s rebuild + ~30s deploy = **~1 minute total**
**Requirements.txt change**: ~2-3 min (full pip reinstall)

This is fast enough for iterative development. The GitHub Actions CI/CD pipeline:
1. Push to `main` → GitHub Actions triggers
2. SSH to GCP server
3. `git pull` + `docker compose build` (cached layers) + `docker compose up -d`
4. Health check

### When to Do a Full/Complete Rebuild

A full rebuild (no layer caching) is only needed:
- When `requirements.txt` changes (new Python packages)
- When the Dockerfile itself changes
- At project finalization (handing over to client)
- When changing deployment target (different domain, different server)

For project finalization / client handover:
```bash
# Full clean rebuild (no cache)
docker compose -f infra/docker/docker-compose.dev.yml build --no-cache
docker compose -f infra/docker/docker-compose.dev.yml up -d
```

This takes 5-10 minutes but only needs to be done once at delivery time.

## Development Cycle

### For each feature/fix:

1. **Make code changes** in the z.ai sandbox
2. **Commit + push** to main
3. **Wait ~1 minute** for GitHub Actions to deploy
4. **Test online** at https://careerjudge.pp.ua
5. **Iterate** — repeat steps 1-4

### Tips to minimize deploy wait time:

- **Batch related changes** — push multiple files in one commit instead of many small commits
- **Use feature branches** — push to a branch, test locally in the sandbox (typecheck/lint/tests), merge to main only when ready to deploy
- **Run `npm run typecheck` + `npm run lint` + `npm test`** in the sandbox BEFORE pushing — catches errors without waiting for deploy
- **The ~30s rebuild is cached** — if you push 5 times in 10 minutes, each deploy is still ~30s (not cumulative)

## Vercel Frontend Auto-Deploy

The frontend is deployed separately on Vercel:
- Vercel auto-builds the frontend on every push to `main`
- Build takes ~1-2 minutes
- Vercel serves the built SPA via CDN
- Caddy proxies `/*` to Vercel (browser stays on careerjudge.pp.ua)

So after pushing:
- **Backend changes**: ~1 minute (GCP Docker rebuild)
- **Frontend changes**: ~1-2 minutes (Vercel build)
- **Both**: ~2 minutes total (parallel)

## Production Deployment (Future)

When ready for production (client handover):

1. **Tag a release**: `git tag v1.0.0 && git push origin v1.0.0`
2. **GitHub Actions CD-prod workflow** triggers:
   - SSH to OCI Ampere A1 (production server)
   - Full Docker rebuild (no cache)
   - Database backup
   - Migration
   - Health check
3. **Client can test** on the production domain
4. **If client wants different domain/server**: update DNS + Caddy config + redeploy

## Summary

| Scenario | Rebuild Type | Time |
|---|---|---|
| Code-only change (backend) | Cached layer rebuild | ~30s |
| Code-only change (frontend) | Vercel build | ~1-2 min |
| requirements.txt change | Full pip reinstall | ~2-3 min |
| Project finalization | Full clean rebuild | ~5-10 min |
| Production deploy (tag) | Full rebuild + backup | ~10-15 min |

**The cached ~30s rebuild is the normal development cycle. Full rebuilds are only for final delivery or infrastructure changes.**
