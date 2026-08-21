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


class AvatarUploadView(APIView):
    """POST /api/me/avatar/ — upload the current user's avatar (Report 3 §1.5).

    Accepts a multipart file upload under the ``avatar`` field and stores it
    on the user's UserProfile.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        avatar = request.FILES.get("avatar")
        if not avatar:
            return Response(
                {"error": {"code": "validation_error", "message": "avatar file is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile = getattr(request.user, "profile", None)
        if profile is None:
            # Create the profile lazily for users that don't have one yet.
            from .models import UserProfile

            profile = UserProfile.objects.create(user=request.user)
        profile.avatar = avatar
        profile.save(update_fields=["avatar"])
        return Response(
            {
                "message": "Avatar uploaded.",
                "data": {
                    "avatar": (
                        request.build_absolute_uri(profile.avatar.url) if profile.avatar else None
                    )
                },
            },
            status=status.HTTP_200_OK,
        )
