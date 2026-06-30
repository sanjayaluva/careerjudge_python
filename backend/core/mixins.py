"""Reusable view mixins."""
from rest_framework.response import Response
from rest_framework import status


class ActionSerializerMixin:
    """Select serializer class based on view.action."""

    serializer_class = None
    serializer_classes: dict[str, type] = {}

    def get_serializer_class(self):
        action = getattr(self, "action", None)
        if action and action in self.serializer_classes:
            return self.serializer_classes[action]
        return self.serializer_class


class CreateUpdateDestroyResponseMixin:
    """Return a normalized success envelope on write actions."""

    def _success(self, data=None, code=200, message="OK"):
        return Response(
            {
                "message": message,
                "data": data or {},
            },
            status=code,
        )
