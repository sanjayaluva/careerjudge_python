"""Admin URL routes — /api/accounts/*."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_admin import (
    AssignPermissionView,
    AssignRoleView,
    RoleViewSet,
    UserViewSet,
)

app_name = "accounts"

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")

urlpatterns = [
    path("", include(router.urls)),
    path("users/<int:user_id>/assign-role", AssignRoleView.as_view(), name="user-assign-role"),
    path(
        "roles/<int:role_id>/assign-permission",
        AssignPermissionView.as_view(),
        name="role-assign-permission",
    ),
]
