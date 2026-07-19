"""URL routes for the Reporting module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GeneratedReportViewSet, ReportViewSet

app_name = "reporting"

router = DefaultRouter()
router.register("reports", ReportViewSet, basename="report")
router.register("generated", GeneratedReportViewSet, basename="generated-report")

urlpatterns = [
    path("", include(router.urls)),
]
