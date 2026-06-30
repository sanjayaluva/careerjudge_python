"""Current-user URL routes — /api/me/*."""

from django.urls import path

from .views_me import ChangePasswordView, MeView

app_name = "me"

urlpatterns = [
    path("", MeView.as_view(), name="me"),
    path("change-password", ChangePasswordView.as_view(), name="change-password"),
]
