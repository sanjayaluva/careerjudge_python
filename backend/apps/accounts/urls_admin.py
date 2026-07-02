"""Admin URL routes — /api/accounts/*."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_admin import (
    AssignPermissionView,
    AssignRoleView,
    BulkUserTemplateView,
    BulkUserUploadView,
    RemovePermissionView,
    RoleViewSet,
    UserViewSet,
)

app_name = "accounts"

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")

urlpatterns = [
    # Bulk user upload — MUST come before router.urls to avoid being
    # matched as a detail view (pk="bulk-upload")
    path(
        "users/bulk-upload/",
        BulkUserUploadView.as_view(),
        name="user-bulk-upload",
    ),
    path(
        "users/bulk-upload/template/",
        BulkUserTemplateView.as_view(),
        name="user-bulk-upload-template",
    ),
    path("", include(router.urls)),
    path("users/<int:user_id>/assign-role/", AssignRoleView.as_view(), name="user-assign-role"),
    path(
        "roles/<int:role_id>/assign-permission/",
        AssignPermissionView.as_view(),
        name="role-assign-permission",
    ),
    path(
        "roles/<int:role_id>/remove-permission/",
        RemovePermissionView.as_view(),
        name="role-remove-permission",
    ),
]
