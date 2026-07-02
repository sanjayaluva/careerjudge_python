"""URL routes for the organizations module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GroupViewSet,
    OrganizationMemberViewSet,
    OrganizationViewSet,
)

app_name = "organizations"

router = DefaultRouter()
router.register("", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<int:organization_id>/groups",
        GroupViewSet.as_view({"get": "list", "post": "create"}),
        name="group-list",
    ),
    path(
        "<int:organization_id>/groups/<int:pk>",
        GroupViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="group-detail",
    ),
    path(
        "<int:organization_id>/members",
        OrganizationMemberViewSet.as_view({"get": "list", "post": "create"}),
        name="member-list",
    ),
    path(
        "<int:organization_id>/members/<int:pk>",
        OrganizationMemberViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="member-detail",
    ),
]
