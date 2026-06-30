"""Views for /api/me/ endpoints (current user profile)."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ChangePasswordSerializer,
    UpdateProfileSerializer,
    UserSerializer,
)


class MeView(APIView):
    """GET /api/me/ — current user details."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(
            {"message": "OK", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Return fresh user data
        request.user.refresh_from_db()
        return Response(
            {"message": "Profile updated.", "data": UserSerializer(request.user).data},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """POST /api/me/change-password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password", "updated_at"])
        return Response(
            {"message": "Password changed successfully.", "data": {}},
            status=status.HTTP_200_OK,
        )
