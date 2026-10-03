"""URL routes for the Career Profiling module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProfilingSolutionModificationRequestViewSet, ProfilingSolutionViewSet

app_name = "career_profiling"

router = DefaultRouter()
router.register("solutions", ProfilingSolutionViewSet, basename="solution")
# Report 9 #107: CJ Admin's approval queue for profiling-solution requests.
router.register(
    "modification-requests",
    ProfilingSolutionModificationRequestViewSet,
    basename="solution-modification-request",
)

urlpatterns = [
    path("", include(router.urls)),
]
