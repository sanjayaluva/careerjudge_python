"""Licensed content an organization manager uses ON BEHALF of his members.

Report 9 (1 Oct 2026), signed basis User Details pp.3-5 ("View Trainings →
Assign Training", "Schedule/Reschedule Training", "View Counsellors →
Schedule/Reschedule Counselling") and Report 4 CJA-12..18:

- courses CJ Admin licensed to the organization: assign / unassign them to
  members (registration on the member's behalf) — #15/#28/#59;
- schedule / reschedule / cancel a licensed course for the organization or a
  group, members notified — #16/#29/#60;
- when counselling is licensed: view counsellors and their open slots, book /
  reschedule / cancel a session FOR a member — #18/#19/#30/#31/#61.

These are organization-nested routes guarded by the organizations rights the
managers already hold (view / change) plus the organization scope
(``ManagedOrgMixin``) — they do not grant the managers the training or
counselling 'add' rights. A Group Admin acts for his group (and sub-groups)
only; Corp Admin / Corp Exclusive / Channel Partner for their organization.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from .models import CourseSchedule, Organization, OrganizationAssignment, OrganizationMember
from .scoping import descendant_group_ids, managed_group_ids, org_has_counseling
from .serializers import CourseScheduleSerializer
from .views import HasOrgContentPermission, ManagedOrgMixin


class HasOrgActingPermission(HasOrgContentPermission):
    """Reading is 'view', acting for members is managing the organization
    ('change') — the right every organization manager holds."""

    action_map = {
        **HasOrgContentPermission.action_map,
        "assign": "change",
        "unassign": "change",
        "timeslots": "view",
        "reschedule": "change",
        "cancel": "change",
    }


def _organization(view) -> Organization:
    return get_object_or_404(Organization, id=view.kwargs.get("organization_id"))


def _member_ids(user, org_id) -> set[int]:
    """The members ``user`` may act for in this organization: its corporate
    individuals / partner users (not its admins), limited to his group and
    sub-groups for a Group Admin."""
    qs = OrganizationMember.objects.filter(
        organization_id=org_id, is_admin=False, user__role__name="individual"
    )
    group_ids = managed_group_ids(user)
    if group_ids is not None:
        qs = qs.filter(group_id__in=group_ids)
    return set(qs.values_list("user_id", flat=True))


def _licensed_course_ids(org_id, user) -> set[int]:
    """Courses the organization's members may be given: those CJ Admin
    licensed to it, plus (Report 9 #47/#52) its own published private
    courses — the latter only for its own people (Report 4 §3)."""
    from apps.training.models import TrainingCourse

    from .views import _sees_org_private_content

    ids = set(
        OrganizationAssignment.objects.filter(
            organization_id=org_id, item_type="training_course"
        ).values_list("item_id", flat=True)
    )
    if _sees_org_private_content(user, org_id):
        ids |= set(
            TrainingCourse.objects.filter(
                owner_organization_id=org_id, status="published"
            ).values_list("id", flat=True)
        )
    return ids


def _licensed_course(org_id, course_id, user):
    from apps.training.models import TrainingCourse

    if int(course_id) not in _licensed_course_ids(org_id, user):
        raise NotFound("This course is not licensed to the organization.")
    return get_object_or_404(TrainingCourse, id=course_id, status="published")


def _user_ids_from(data, *keys) -> list[int]:
    for key in keys:
        value = data.get(key)
        if value in (None, ""):
            continue
        values = value if isinstance(value, list) else [value]
        try:
            return [int(v) for v in values]
        except (TypeError, ValueError) as exc:
            raise ValidationError({key: "Expected user ids."}) from exc
    raise ValidationError({keys[0]: "Pick at least one member."})


# ---------------------------------------------------------------------------
# Licensed courses: assign / unassign to members (#15/#28/#59)
# ---------------------------------------------------------------------------


class OrgCourseViewSet(ManagedOrgMixin, ViewSet):
    """GET  /api/organizations/<org_id>/courses/                 licensed courses + members
    POST /api/organizations/<org_id>/courses/<id>/assign/      {"user_ids": [..]}
    POST /api/organizations/<org_id>/courses/<id>/unassign/    {"user_id": ..}
    """

    permission_classes = [IsAuthenticated, HasOrgActingPermission]

    def list(self, request, organization_id=None):
        from apps.training.models import CourseRegistration, TrainingCourse
        from apps.training.services import can_unassign

        member_ids = _member_ids(request.user, organization_id)
        courses = TrainingCourse.objects.filter(
            id__in=_licensed_course_ids(organization_id, request.user), status="published"
        ).order_by("title")
        regs = (
            CourseRegistration.objects.filter(course__in=courses, student_id__in=member_ids)
            .select_related("student")
            .prefetch_related("progress_records")
            .order_by("student__full_name", "student__email")
        )
        by_course: dict[int, list] = {}
        for reg in regs:
            by_course.setdefault(reg.course_id, []).append(
                {
                    "registration_id": reg.id,
                    "user_id": reg.student_id,
                    "full_name": reg.student.full_name,
                    "email": reg.student.email,
                    "completion_status": reg.completion_status,
                    "assigned_by_organization": reg.organization_id == int(organization_id),
                    "can_unassign": reg.organization_id == int(organization_id)
                    and can_unassign(reg),
                }
            )
        data = [
            {
                "id": c.id,
                "title": c.title,
                "course_type": c.course_type,
                "schedule_type": c.schedule_type,
                "duration_days": c.duration_days,
                "members": by_course.get(c.id, []),
            }
            for c in courses
        ]
        return Response({"message": "OK", "data": data}, status=status.HTTP_200_OK)

    def assign(self, request, organization_id=None, pk=None):
        """Register members for the licensed course on their behalf. The
        organization's licence pays for it: no fee for the member."""
        from apps.accounts.models import User
        from apps.training.services import assign_course_for_organization

        org = _organization(self)
        course = _licensed_course(org.id, pk, request.user)
        user_ids = _user_ids_from(request.data, "user_ids", "user_id")
        allowed = _member_ids(request.user, org.id)
        if not set(user_ids) <= allowed:
            raise PermissionDenied(
                "You can assign courses only to the members of your organization"
                + (" group." if managed_group_ids(request.user) is not None else ".")
            )
        assigned, already = [], []
        for student in User.objects.filter(id__in=user_ids):
            _reg, created = assign_course_for_organization(course, student, org, request.user)
            (assigned if created else already).append(student.id)
        message = f"Assigned '{course.title}' to {len(assigned)} member(s)."
        if already:
            message += f" {len(already)} already registered."
        return Response(
            {"message": message, "data": {"assigned": assigned, "already_registered": already}},
            status=status.HTTP_200_OK,
        )

    def unassign(self, request, organization_id=None, pk=None):
        """Withdraw a registration made through this organization, as long as
        the member has not started the course."""
        from apps.training.models import CourseRegistration
        from apps.training.services import can_unassign, unassign_course_for_organization

        org = _organization(self)
        course = _licensed_course(org.id, pk, request.user)
        (user_id,) = _user_ids_from(request.data, "user_id")[:1]
        if user_id not in _member_ids(request.user, org.id):
            raise NotFound("Member not found.")
        reg = CourseRegistration.objects.filter(
            course=course, student_id=user_id, organization=org
        ).first()
        if reg is None:
            raise NotFound("This member was not assigned the course by the organization.")
        if not can_unassign(reg):
            raise ValidationError(
                {"user_id": "The member has already started this course; it can't be unassigned."}
            )
        unassign_course_for_organization(reg)
        return Response(
            {"message": f"'{course.title}' unassigned.", "data": {}},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Course schedules (#16/#29/#60) — parallel to AssessmentScheduleViewSet
# ---------------------------------------------------------------------------


class CourseScheduleViewSet(ManagedOrgMixin, ModelViewSet):
    """GET/POST         /api/organizations/<org_id>/course-schedules/
    GET/PATCH/DELETE /api/organizations/<org_id>/course-schedules/<id>/

    PATCH reschedules, DELETE cancels; the targeted members are notified each
    time."""

    serializer_class = CourseScheduleSerializer
    permission_classes = [IsAuthenticated, HasOrgActingPermission]

    def get_queryset(self):
        org_id = self.kwargs.get("organization_id")
        qs = CourseSchedule.objects.filter(organization_id=org_id).select_related("course", "group")
        from .views import _sees_org_private_content

        if not _sees_org_private_content(self.request.user, org_id):
            qs = qs.filter(course__owner_organization__isnull=True)
        group_ids = managed_group_ids(self.request.user)
        if group_ids is not None:
            qs = qs.filter(group_id__in=group_ids)
        return qs

    def _validate_target(self, course, group):
        """Only a course licensed to the organization (published); a Group
        Admin only for his group."""
        org_id = int(self.kwargs.get("organization_id"))
        if course is not None and (
            course.status != "published"
            or course.id not in _licensed_course_ids(org_id, self.request.user)
        ):
            raise PermissionDenied(
                "This course has not been licensed to your organization by CJ Admin."
            )
        if group is not None and group.organization_id != org_id:
            raise PermissionDenied("That group belongs to another organization.")
        group_ids = managed_group_ids(self.request.user)
        if group_ids is not None and (group is None or group.id not in group_ids):
            raise PermissionDenied("You can schedule courses only for your own group.")

    def _notify_members(self, schedule, event="scheduled"):
        from apps.notifications.models import notify_user

        members = OrganizationMember.objects.filter(
            organization=schedule.organization, is_admin=False
        ).select_related("user")
        if schedule.group_id:
            members = members.filter(
                group_id__in=[schedule.group_id, *descendant_group_ids([schedule.group_id])]
            )
        when = timezone.localtime(schedule.scheduled_at).strftime("%d %b %Y, %H:%M")
        title, body = {
            "scheduled": (
                "Course scheduled",
                f"'{schedule.course.title}' is scheduled for {when}.",
            ),
            "rescheduled": (
                "Course rescheduled",
                f"'{schedule.course.title}' has been rescheduled to {when}.",
            ),
            "cancelled": (
                "Course schedule cancelled",
                f"'{schedule.course.title}' scheduled for {when} has been cancelled.",
            ),
        }[event]
        for m in members:
            notify_user(m.user, title, body, "info", f"/training/{schedule.course_id}")
        if event != "cancelled":
            schedule.notified = True
            schedule.save(update_fields=["notified"])

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        return Response(
            {"message": "OK", "data": self.get_serializer(self.get_object()).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._validate_target(
            serializer.validated_data.get("course"), serializer.validated_data.get("group")
        )
        schedule = serializer.save(organization=_organization(self), created_by=request.user)
        self._notify_members(schedule)
        return Response(
            {
                "message": "Course scheduled and members notified.",
                "data": CourseScheduleSerializer(schedule).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self._validate_target(
            serializer.validated_data.get("course", instance.course),
            serializer.validated_data.get("group", instance.group),
        )
        schedule = serializer.save()
        self._notify_members(schedule, "rescheduled")
        return Response(
            {
                "message": "Course rescheduled and members notified.",
                "data": CourseScheduleSerializer(schedule).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._notify_members(instance, "cancelled")
        instance.delete()
        return Response(
            {"message": "Course schedule cancelled and members notified.", "data": {}},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Counselling for members (#18/#19/#30/#31/#61)
# ---------------------------------------------------------------------------


def _require_counseling_licence(view):
    if not org_has_counseling(view.kwargs.get("organization_id")):
        raise PermissionDenied(
            "Counselling is not licensed to this organization. Please contact CJ Admin."
        )


class OrgCounsellorViewSet(ManagedOrgMixin, ViewSet):
    """GET /api/organizations/<org_id>/counsellors/                 available counsellors
    GET /api/organizations/<org_id>/counsellors/<id>/timeslots/  open future slots
    """

    permission_classes = [IsAuthenticated, HasOrgActingPermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        _require_counseling_licence(self)

    @staticmethod
    def _counsellors():
        from apps.counseling.models import CounsellorProfile

        return CounsellorProfile.objects.filter(
            user__is_active=True, user__role__name="counsellor"
        ).select_related("user", "user__profile")

    def list(self, request, organization_id=None):
        from apps.counseling.serializers import CounsellorProfileSerializer

        counsellors = [c for c in self._counsellors().order_by("user__full_name") if c.is_available]
        return Response(
            {
                "message": "OK",
                "data": CounsellorProfileSerializer(
                    counsellors, many=True, context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def timeslots(self, request, organization_id=None, pk=None):
        from datetime import timedelta

        from apps.counseling.models import CounselingSettings
        from apps.counseling.serializers import TimeSlotSerializer

        counsellor = get_object_or_404(self._counsellors(), id=pk)
        now = timezone.now()
        slots = counsellor.timeslots.filter(
            status="available",
            session__isnull=True,
            start_time__gt=now,
            start_time__lte=now + timedelta(weeks=CounselingSettings.get().max_weeks_ahead),
        ).order_by("start_time")
        return Response(
            {"message": "OK", "data": TimeSlotSerializer(slots, many=True).data},
            status=status.HTTP_200_OK,
        )


class OrgCounselingSessionViewSet(ManagedOrgMixin, ViewSet):
    """GET  /api/organizations/<org_id>/counseling-sessions/                 sessions booked by the organization
    POST /api/organizations/<org_id>/counseling-sessions/                 book for a member
    POST /api/organizations/<org_id>/counseling-sessions/<id>/reschedule/ {"timeslot": id}
    POST /api/organizations/<org_id>/counseling-sessions/<id>/cancel/     {"reason": "..."}

    Booking reuses ``apps.counseling.services`` (slot availability, counsellor
    / Help Desk notifications). Counselling is licensed to the organization,
    so the member pays nothing for these sessions.
    """

    permission_classes = [IsAuthenticated, HasOrgActingPermission]

    def _sessions(self):
        from apps.counseling.models import CounselingSession

        org_id = self.kwargs.get("organization_id")
        return CounselingSession.objects.filter(
            organization_id=org_id,
            counselee_id__in=_member_ids(self.request.user, org_id),
        ).select_related("counselee", "counsellor__user", "category", "timeslot")

    def _session(self, pk):
        session = self._sessions().filter(id=pk).first()
        if session is None:
            raise NotFound("Session not found.")
        return session

    @staticmethod
    def _error(exc):
        return Response(
            {"error": {"code": "validation_error", "message": str(exc), "details": {}}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def list(self, request, organization_id=None):
        from apps.counseling.serializers import CounselingSessionSerializer

        sessions = self._sessions().order_by("-timeslot__start_time")
        return Response(
            {"message": "OK", "data": CounselingSessionSerializer(sessions, many=True).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, organization_id=None):
        from apps.accounts.models import User
        from apps.counseling.models import CounselingCategory, CounsellorProfile, TimeSlot
        from apps.counseling.serializers import CounselingSessionSerializer
        from apps.counseling.services import BookingError, book_session

        _require_counseling_licence(self)
        org = _organization(self)
        data = request.data
        (counselee_id,) = _user_ids_from(data, "counselee")[:1]
        if counselee_id not in _member_ids(request.user, org.id):
            raise PermissionDenied(
                "You can book counselling only for the members of your organization"
                + (" group." if managed_group_ids(request.user) is not None else ".")
            )
        topic = (data.get("topic") or "").strip()
        if not topic:
            raise ValidationError({"topic": "Enter the topic for counselling."})
        mode = data.get("mode") or "online"
        if mode not in ("online", "offline"):
            raise ValidationError({"mode": "Mode must be online or offline."})
        counsellor = get_object_or_404(
            CounsellorProfile, id=data.get("counsellor"), user__is_active=True
        )
        timeslot = get_object_or_404(TimeSlot, id=data.get("timeslot"))
        if timeslot.start_time <= timezone.now():
            return self._error("Pick a time slot in the future.")
        category = None
        if data.get("category"):
            category = get_object_or_404(CounselingCategory, id=data.get("category"))
        try:
            session, _ = book_session(
                counselee=User.objects.get(id=counselee_id),
                counsellor=counsellor,
                timeslot=timeslot,
                category=category,
                topic=topic,
                description=data.get("description", ""),
                mode=mode,
                organization=org,
                booked_by=request.user,
            )
        except BookingError as exc:
            return self._error(exc)
        return Response(
            {
                "message": "Session booked for the member. Awaiting counsellor confirmation.",
                "data": CounselingSessionSerializer(session).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def reschedule(self, request, organization_id=None, pk=None):
        from apps.counseling.models import TimeSlot
        from apps.counseling.serializers import CounselingSessionSerializer
        from apps.counseling.services import BookingError, reschedule_session

        _require_counseling_licence(self)
        session = self._session(pk)
        timeslot = get_object_or_404(TimeSlot, id=request.data.get("timeslot"))
        try:
            reschedule_session(session, timeslot)
        except BookingError as exc:
            return self._error(exc)
        return Response(
            {
                "message": "Session rescheduled. The counsellor and the member were notified.",
                "data": CounselingSessionSerializer(session).data,
            },
            status=status.HTTP_200_OK,
        )

    def cancel(self, request, organization_id=None, pk=None):
        from apps.counseling.serializers import CounselingSessionSerializer
        from apps.counseling.services import BookingError, cancel_session

        session = self._session(pk)
        try:
            cancel_session(session, cancelled_by="organization", reason=request.data.get("reason"))
        except BookingError as exc:
            return self._error(exc)
        return Response(
            {
                "message": "Session cancelled. The counsellor and the member were notified.",
                "data": CounselingSessionSerializer(session).data,
            },
            status=status.HTTP_200_OK,
        )
