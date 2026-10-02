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
from .views_licensing import (
    CourseScheduleViewSet,
    OrgCounselingSessionViewSet,
    OrgCounsellorViewSet,
    OrgCourseViewSet,
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
    # Report 9 #21: the Corp Admin defines a Group Admin for a group.
    path(
        "<int:organization_id>/group-admins/",
        OrganizationMemberViewSet.as_view({"post": "create_group_admin"}),
        name="group-admin-create",
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
    # Report 9 #15/#16/#18/#19 (+ group admin / channel partner): licensed
    # courses and counselling used by a manager on behalf of his members.
    path(
        "<int:organization_id>/courses/",
        OrgCourseViewSet.as_view({"get": "list"}),
        name="org-course-list",
    ),
    path(
        "<int:organization_id>/courses/<int:pk>/assign/",
        OrgCourseViewSet.as_view({"post": "assign"}),
        name="org-course-assign",
    ),
    path(
        "<int:organization_id>/courses/<int:pk>/unassign/",
        OrgCourseViewSet.as_view({"post": "unassign"}),
        name="org-course-unassign",
    ),
    path(
        "<int:organization_id>/course-schedules/",
        CourseScheduleViewSet.as_view({"get": "list", "post": "create"}),
        name="course-schedule-list",
    ),
    path(
        "<int:organization_id>/course-schedules/<int:pk>/",
        CourseScheduleViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="course-schedule-detail",
    ),
    path(
        "<int:organization_id>/counsellors/",
        OrgCounsellorViewSet.as_view({"get": "list"}),
        name="org-counsellor-list",
    ),
    path(
        "<int:organization_id>/counsellors/<int:pk>/timeslots/",
        OrgCounsellorViewSet.as_view({"get": "timeslots"}),
        name="org-counsellor-timeslots",
    ),
    path(
        "<int:organization_id>/counseling-sessions/",
        OrgCounselingSessionViewSet.as_view({"get": "list", "post": "create"}),
        name="org-counseling-session-list",
    ),
    path(
        "<int:organization_id>/counseling-sessions/<int:pk>/reschedule/",
        OrgCounselingSessionViewSet.as_view({"post": "reschedule"}),
        name="org-counseling-session-reschedule",
    ),
    path(
        "<int:organization_id>/counseling-sessions/<int:pk>/cancel/",
        OrgCounselingSessionViewSet.as_view({"post": "cancel"}),
        name="org-counseling-session-cancel",
    ),
    # Public tenant branding by slug (no auth) — must be a literal path segment
    # that cannot collide with the numeric <organization_id> routes above.
    path("site/<slug:slug>/", CorporateSitePublicView.as_view(), name="site-public"),
    path("site/<slug:slug>/logo/", CorporateSiteLogoView.as_view(), name="site-logo"),
]
