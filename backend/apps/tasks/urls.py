"""URL routes for the Task Management module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TaskExtensionViewSet, TaskViewSet

app_name = "tasks"

router = DefaultRouter()
router.register("", TaskViewSet, basename="task")
router.register("extensions", TaskExtensionViewSet, basename="extension")

urlpatterns = [
    path("", include(router.urls)),
]
