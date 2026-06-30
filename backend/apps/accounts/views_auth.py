"""Views for auth endpoints (signup, login, logout, verify, reset)."""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    EmailVerificationSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    ResendVerificationSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
)
from .services import (
    create_email_verification_token,
    create_password_reset_token,
    send_password_reset_email,
    send_verification_email,
)
from .services import (
    reset_password as svc_reset_password,
)
from .services import (
    verify_email as svc_verify_email,
)


class SignupView(APIView):
    """POST /api/auth/signup — UC001."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create verification token and send email
        token = create_email_verification_token(user)
        try:
            send_verification_email(user, token)
        except Exception:
            # Email send failure should not block signup
            pass

        return Response(
            {
                "message": (
                    "Account created. An email with an activation link has been "
                    "sent to your registered email. Please follow the instructions "
                    "to complete registration."
                ),
                "data": {"email": user.email, "user_id": user.id},
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/auth/login — UC007. Returns access + refresh tokens."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Login successful.",
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "role": user.role.name if user.role else None,
                        "is_email_verified": user.is_email_verified,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """POST /api/auth/logout — blacklist the refresh token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Refresh token required.",
                        "details": {"refresh": ["This field is required."]},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {
                    "error": {
                        "code": "invalid_token",
                        "message": "Invalid or expired refresh token.",
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": "Logout successful.", "data": {}},
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    """POST /api/auth/token/refresh — rotate refresh token."""

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Refresh token required.",
                        "details": {"refresh": ["This field is required."]},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            refresh = RefreshToken(refresh_token)
            access = refresh.access_token
            # Rotate: blacklist old, return new refresh
            try:
                refresh.blacklist()
            except Exception:
                pass
            new_refresh = RefreshToken.for_user(refresh.user)
            return Response(
                {
                    "message": "Token refreshed.",
                    "data": {
                        "access": str(access),
                        "refresh": str(new_refresh),
                    },
                },
                status=status.HTTP_200_OK,
            )
        except TokenError:
            return Response(
                {
                    "error": {
                        "code": "invalid_token",
                        "message": "Invalid or expired refresh token.",
                        "details": {},
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )


class VerifyEmailView(APIView):
    """POST /api/auth/verify-email — UC001 activation."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        user = svc_verify_email(token)
        return Response(
            {
                "message": "Email verified successfully. Registration complete.",
                "data": {"email": user.email, "user_id": user.id},
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    """POST /api/auth/resend-verification."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email__iexact=email)
            if not user.is_email_verified:
                token = create_email_verification_token(user)
                try:
                    send_verification_email(user, token)
                except Exception:
                    pass
        except User.DoesNotExist:
            # Silent — do not leak existence
            pass
        return Response(
            {
                "message": (
                    "If an account with that email exists and is not yet verified, "
                    "a new activation link has been sent."
                ),
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    """POST /api/auth/forgot-password."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
            token = create_password_reset_token(user)
            try:
                send_password_reset_email(user, token)
            except Exception:
                pass
        except User.DoesNotExist:
            pass
        return Response(
            {
                "message": (
                    "If an account with that email exists, a password reset link " "has been sent."
                ),
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """POST /api/auth/reset-password."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        user = svc_reset_password(token, serializer.validated_data["password"])
        return Response(
            {"message": "Password reset successfully.", "data": {"email": user.email}},
            status=status.HTTP_200_OK,
        )
