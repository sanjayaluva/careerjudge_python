"""URL routes for the Task Management module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConcernViewSet, TaskExtensionViewSet, TaskViewSet

app_name = "tasks"

router = DefaultRouter()
router.register("concerns", ConcernViewSet, basename="concern")
router.register("extensions", TaskExtensionViewSet, basename="extension")
router.register("", TaskViewSet, basename="task")

urlpatterns = [
    path("", include(router.urls)),
]
