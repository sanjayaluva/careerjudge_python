"""Views for the Notifications module.

Endpoints:
  GET    /api/notifications/                      — list my notifications (paginated)
  GET    /api/notifications/unread_count/         — get unread count (for bell badge)
  POST   /api/notifications/<id>/mark_read/       — mark single notification as read
  POST   /api/notifications/mark_all_read/        — mark all as read
  DELETE /api/notifications/<id>/                 — delete a notification
"""

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """User-facing notification endpoints.

    Users see only their own notifications. No create via API —
    notifications are created programmatically by the system
    (via notify_user / notify_role helper functions).
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]  # no create/put/patch

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """GET /api/notifications/unread_count/ — returns the unread count.

        Used by the bell-icon badge to show how many unread notifications exist.
        Polled every 30 seconds by the frontend.
        """
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response(
            {"message": "OK", "data": {"unread_count": count}}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """POST /api/notifications/<id>/mark_read/ — mark a single notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response(
            {"message": "Marked as read.", "data": NotificationSerializer(notification).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """POST /api/notifications/mark_all_read/ — mark ALL notifications as read."""
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"message": "All notifications marked as read."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """DELETE /api/notifications/<id>/ — delete a notification."""
        notification = self.get_object()
        notification.delete()
        return Response({"message": "Notification deleted."}, status=status.HTTP_200_OK)
