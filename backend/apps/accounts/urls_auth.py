"""Auth URL routes — /api/auth/*."""

from django.urls import path

from .views_auth import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    ResendVerificationView,
    ResetPasswordView,
    SignupView,
    VerifyEmailView,
)
from .views_auth import (
    TokenRefreshView as CustomTokenRefreshView,
)

app_name = "auth"

urlpatterns = [
    path("signup", SignupView.as_view(), name="signup"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("token/refresh", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("verify-email", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification", ResendVerificationView.as_view(), name="resend-verification"),
    path("forgot-password", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password", ResetPasswordView.as_view(), name="reset-password"),
]
