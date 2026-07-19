"""URL routes for the Career Profiling module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProfilingSolutionViewSet

app_name = "career_profiling"

router = DefaultRouter()
router.register("solutions", ProfilingSolutionViewSet, basename="solution")

urlpatterns = [
    path("", include(router.urls)),
]
