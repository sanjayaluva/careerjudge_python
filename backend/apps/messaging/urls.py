"""URL routes for the Messaging module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConversationViewSet, MessageViewSet

app_name = "messaging"

router = DefaultRouter()
router.register("messages", MessageViewSet, basename="message")
router.register("conversations", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("", include(router.urls)),
]
