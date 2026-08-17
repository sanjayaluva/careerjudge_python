"""Serializers for the Messaging module."""

from django.db.models import Q
from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True, default="")
    recipient_name = serializers.CharField(source="recipient.full_name", read_only=True, default="")
    sender_role = serializers.CharField(source="sender.role.name", read_only=True, default="")
    recipient_role = serializers.CharField(source="recipient.role.name", read_only=True, default="")

    class Meta:
        model = Message
        fields = [
            "id",
            "sender",
            "sender_name",
            "sender_role",
            "recipient",
            "recipient_name",
            "recipient_role",
            "subject",
            "body",
            "is_read",
            "read_at",
            "parent",
            "created_at",
        ]
        read_only_fields = ["id", "sender", "is_read", "read_at", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    user1_name = serializers.CharField(source="user1.full_name", read_only=True, default="")
    user2_name = serializers.CharField(source="user2.full_name", read_only=True, default="")
    user1_role = serializers.CharField(source="user1.role.name", read_only=True, default="")
    user2_role = serializers.CharField(source="user2.role.name", read_only=True, default="")
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "user1",
            "user1_name",
            "user1_role",
            "user2",
            "user2_name",
            "user2_role",
            "last_message_at",
            "last_message_preview",
            "unread_count",
            "created_at",
        ]
        read_only_fields = ["id", "user1", "user2", "last_message_at", "created_at"]

    def get_last_message_preview(self, obj):
        last = (
            Message.objects.filter(
                Q(sender=obj.user1, recipient=obj.user2) | Q(sender=obj.user2, recipient=obj.user1)
            )
            .order_by("-created_at")
            .first()
        )
        if last:
            return last.body[:100]
        return ""

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return Message.objects.filter(
            Q(sender=obj.user1, recipient=obj.user2) | Q(sender=obj.user2, recipient=obj.user1),
            recipient=request.user,
            is_read=False,
        ).count()
