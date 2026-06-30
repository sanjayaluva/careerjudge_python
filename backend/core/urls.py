"""Project-level URL routing for health checks."""
from django.urls import path
from .urls_health import health, health_db

urlpatterns = [
    path("", health),
    path("db/", health_db),
]
