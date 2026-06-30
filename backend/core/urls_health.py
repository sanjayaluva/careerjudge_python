"""Health check URLs — included directly at /api/health/."""

from django.db import connection
from django.http import JsonResponse
from django.urls import path


def health(request):
    """Liveness probe — always 200 if process is alive."""
    return JsonResponse({"status": "ok"})


def health_db(request):
    """Readiness probe — checks DB connectivity."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return JsonResponse({"status": "ok", "db": "up"})
    except Exception as e:
        return JsonResponse(
            {"status": "error", "db": "down", "error": str(e)},
            status=503,
        )


urlpatterns = [
    path("", health),
    path("db/", health_db),
]
