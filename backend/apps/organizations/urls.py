"""URL routes for the organizations module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssessmentScheduleViewSet,
    CorporateSiteLogoView,
    CorporateSitePublicView,
    CorporateWebsiteViewSet,
    GroupViewSet,
    MyCorporateSiteView,
    OrganizationAssignmentViewSet,
    OrganizationMemberViewSet,
    OrganizationViewSet,
)

app_name = "organizations"

router = DefaultRouter()
router.register("", OrganizationViewSet, basename="organization")

urlpatterns = [
    # Report 9 #51/#52: before the router, whose detail route would otherwise
    # read "my-site" as an organization pk.
    path("my-site/", MyCorporateSiteView.as_view(), name="my-site"),
    path("", include(router.urls)),
    path(
        "<int:organization_id>/groups/",
        GroupViewSet.as_view({"get": "list", "post": "create"}),
        name="group-list",
    ),
    path(
        "<int:organization_id>/groups/<int:pk>/",
        GroupViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="group-detail",
    ),
    path(
        "<int:organization_id>/members/",
        OrganizationMemberViewSet.as_view({"get": "list", "post": "create"}),
        name="member-list",
    ),
    path(
        "<int:organization_id>/members/<int:pk>/",
        OrganizationMemberViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="member-detail",
    ),
    path(
        "<int:organization_id>/assignments/",
        OrganizationAssignmentViewSet.as_view({"get": "list", "post": "create"}),
        name="assignment-list",
    ),
    path(
        "<int:organization_id>/assignments/<int:pk>/",
        OrganizationAssignmentViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="assignment-detail",
    ),
    path(
        "<int:organization_id>/schedules/",
        AssessmentScheduleViewSet.as_view({"get": "list", "post": "create"}),
        name="schedule-list",
    ),
    path(
        "<int:organization_id>/schedules/<int:pk>/",
        AssessmentScheduleViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="schedule-detail",
    ),
    path(
        "<int:organization_id>/website/",
        CorporateWebsiteViewSet.as_view(
            {"get": "retrieve", "post": "create", "patch": "partial_update"}
        ),
        name="website",
    ),
    # Public tenant branding by slug (no auth) — must be a literal path segment
    # that cannot collide with the numeric <organization_id> routes above.
    path("site/<slug:slug>/", CorporateSitePublicView.as_view(), name="site-public"),
    path("site/<slug:slug>/logo/", CorporateSiteLogoView.as_view(), name="site-logo"),
]
