"""Views for the Messaging module.

Endpoints:
  GET/POST   /api/messaging/messages/          — list/create messages
  GET/PATCH  /api/messaging/messages/<id>/     — retrieve/mark-as-read
  POST       /api/messaging/messages/<id>/reply/ — reply to a message
  GET        /api/messaging/conversations/     — list conversations
  GET        /api/messaging/conversations/<id>/ — view conversation thread
  GET        /api/messaging/conversations/contacts/ — list available contacts by role
"""

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.models import User

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


class MessageViewSet(ModelViewSet):
    """Message CRUD + reply + mark-as-read."""

    queryset = Message.objects.select_related("sender", "recipient", "parent")
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(Q(sender=user) | Q(recipient=user))

    def create(self, request, *args, **kwargs):
        """Send a message to another user."""
        recipient_id = request.data.get("recipient")
        if not recipient_id:
            return Response(
                {"error": {"code": "validation_error", "message": "recipient is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            recipient = User.objects.get(id=recipient_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Recipient not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create or get conversation
        user1, user2 = sorted([request.user, recipient], key=lambda u: u.id)
        conversation, _ = Conversation.objects.get_or_create(user1=user1, user2=user2)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=request.user)
        conversation.last_message_at = message.created_at
        conversation.save(update_fields=["last_message_at"])

        return Response(
            {"message": "Message sent.", "data": MessageSerializer(message).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        """Reply to a specific message."""
        parent = self.get_object()
        if parent.recipient_id != request.user.id and parent.sender_id != request.user.id:
            return Response(
                {"error": {"code": "forbidden", "message": "Not your message."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        recipient = parent.sender if parent.recipient_id == request.user.id else parent.recipient
        body = request.data.get("body", "")
        if not body:
            return Response(
                {"error": {"code": "validation_error", "message": "body is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            subject=f"Re: {parent.subject}" if parent.subject else "",
            body=body,
            parent=parent,
        )
        return Response(
            {"message": "Reply sent.", "data": MessageSerializer(message).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"])
    def mark_read(self, request, pk=None):
        """Mark a message as read."""
        message = self.get_object()
        if message.recipient_id != request.user.id:
            return Response(
                {"error": {"code": "forbidden", "message": "Not your message."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        from django.utils import timezone

        message.is_read = True
        message.read_at = timezone.now()
        message.save(update_fields=["is_read", "read_at"])
        return Response({"message": "Marked as read."})


class ConversationViewSet(ModelViewSet):
    """List conversations + view thread + contacts."""

    queryset = Conversation.objects.select_related("user1", "user2")
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(Q(user1=user) | Q(user2=user))

    def list(self, request, *args, **kwargs):
        # Wrap in the standard {message, data} envelope so the frontend's
        # apiGetPaged helper (which unwraps `data`) can read the page.
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def thread(self, request, pk=None):
        """Get all messages in a conversation."""
        conversation = self.get_object()
        messages = Message.objects.filter(
            Q(sender=conversation.user1, recipient=conversation.user2)
            | Q(sender=conversation.user2, recipient=conversation.user1)
        ).order_by("created_at")
        return Response({"message": "OK", "data": MessageSerializer(messages, many=True).data})

    @action(detail=False, methods=["get"])
    def contacts(self, request):
        """List available contacts (users the current user can message).

        Per Doc 4: users can message CJ Admin and Helpdesk.
        Also: Corp Admin → Group Admin; Group Admin → Corp Admin;
        SME/Reviewer/Trainer/Counsellor → CJ Admin/Helpdesk.
        """
        user = request.user
        role_name = user.role.name if user.role_id else None

        contactable_roles = []
        if role_name in (
            # Standard Individual User: "Send Message" is a signed capability
            # (User Details.pdf p.1, PLT-1) — they reach CJ Admin + Helpdesk.
            "individual",
            "corp_admin",
            "group_admin",
            "corp_exclusive",
            "channel_partner",
            "sme",
            "reviewer",
            "trainer",
            "counsellor",
        ):
            contactable_roles = ["cj_admin", "helpdesk"]
        elif role_name == "cj_admin":
            contactable_roles = [
                "individual",
                "corp_admin",
                "group_admin",
                "corp_exclusive",
                "channel_partner",
                "sme",
                "reviewer",
                "trainer",
                "counsellor",
                "helpdesk",
            ]
        elif role_name == "helpdesk":
            contactable_roles = [
                "individual",
                "cj_admin",
                "corp_admin",
                "group_admin",
                "corp_exclusive",
                "channel_partner",
                "sme",
                "reviewer",
                "trainer",
                "counsellor",
            ]

        contacts = (
            User.objects.filter(
                is_active=True,
                role__name__in=contactable_roles,
            )
            .exclude(id=user.id)
            .values("id", "email", "full_name", "role__name")
        )

        return Response({"message": "OK", "data": list(contacts)})
