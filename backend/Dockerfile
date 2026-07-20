# Backend Dockerfile — multi-stage build for smaller image
# Uses psycopg2-binary (no libpq build needed) and skips WeasyPrint in Phase 1
# (PDF report generation is Phase 3 — we'll add cairo/pango deps when we need them)
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Minimal build deps — only what pip needs to compile packages without wheels.
# psycopg2-binary ships as a wheel → no libpq-dev needed.
# All other deps (cryptography, etc.) ship as wheels on linux/amd64.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# Runtime deps: libpq5 (psycopg2 runtime), curl (healthcheck),
# plus WeasyPrint system deps (libpango, libcairo, libgobject) for PDF
# report generation (Phase 3 — SRS 04/06 reporting).
# Note: libgdk-pixbuf2.0-0 is intentionally omitted — it's optional for
# WeasyPrint (only needed for some image formats) and the package name
# changed in Debian Trixie (python:3.12-slim base). We only render text
# and tables in PDFs, so it's not needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libglib2.0-0 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 cj

COPY --from=builder /opt/venv /opt/venv
COPY --chown=cj:cj . /app

# Create writable directories for the cj user (collectstatic, staticfiles, media)
# These are referenced in config/settings/base.py: STATIC_ROOT, MEDIA_ROOT
RUN mkdir -p /app/static_collected /app/media /app/staticfiles && \
    chown -R cj:cj /app/static_collected /app/media /app/staticfiles

USER cj

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
