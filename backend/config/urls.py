"""Root URL configuration."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls_auth", namespace="auth")),
    path("api/me/", include("apps.accounts.urls_me", namespace="me")),
    path("api/accounts/", include("apps.accounts.urls_admin", namespace="accounts")),
    path(
        "api/organizations/",
        include("apps.organizations.urls", namespace="organizations"),
    ),
    path(
        "api/question-bank/",
        include("apps.question_bank.urls", namespace="question_bank"),
    ),
    path(
        "api/",
        include("apps.assessment.urls", namespace="assessment"),
    ),
    path(
        "api/career-profiling/",
        include("apps.career_profiling.urls", namespace="career_profiling"),
    ),
    path("api/reporting/", include("apps.reporting.urls", namespace="reporting")),
    path("api/training/", include("apps.training.urls", namespace="training")),
    path("api/notifications/", include("apps.notifications.urls", namespace="notifications")),
    # Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Health
    path("api/health/", include("core.urls_health")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
