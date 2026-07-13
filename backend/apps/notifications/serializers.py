"""Serializers for the Notifications module."""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_label = serializers.CharField(
        source="get_notification_type_display", read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "notification_type_label",
            "title",
            "message",
            "link",
            "is_read",
            "created_at",
            "read_at",
        ]
        read_only_fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "link",
            "is_read",
            "created_at",
            "read_at",
        ]
