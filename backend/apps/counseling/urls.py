"""URL routes for the Counseling module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CounselingCategoryViewSet,
    CounselingSessionViewSet,
    CounselingSettingsViewSet,
    CounsellorProfileViewSet,
    FollowupSessionViewSet,
    TimeSlotViewSet,
)

app_name = "counseling"

router = DefaultRouter()
router.register("categories", CounselingCategoryViewSet, basename="category")
router.register("counsellors", CounsellorProfileViewSet, basename="counsellor")
router.register("timeslots", TimeSlotViewSet, basename="timeslot")
router.register("sessions", CounselingSessionViewSet, basename="session")
router.register("followups", FollowupSessionViewSet, basename="followup")
router.register("settings", CounselingSettingsViewSet, basename="settings")

urlpatterns = [
    path("", include(router.urls)),
]
