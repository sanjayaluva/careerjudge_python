"""Views for the Training module.

Endpoints:
  GET/POST  /api/training/categories/                  — list/create categories
  GET/PATCH /api/training/categories/<id>/              — retrieve/update
  DELETE    /api/training/categories/<id>/              — delete
  GET/POST  /api/training/courses/                      — list/create courses
  GET/PATCH /api/training/courses/<id>/                 — retrieve/update
  DELETE    /api/training/courses/<id>/                 — delete (admin only)
  POST      /api/training/courses/<id>/publish/         — publish course
  GET/POST  /api/training/courses/<id>/lessons/         — list/add lessons
  GET/POST  /api/training/courses/<id>/live-sessions/   — list/add live sessions
  GET/POST  /api/training/courses/<id>/assessments/     — list/add assessments
  POST      /api/training/courses/<id>/register/        — student registers
  GET       /api/training/courses/<id>/registrations/   — trainer views registrations
  GET/POST  /api/training/registrations/<id>/progress/  — list/add progress
  GET       /api/training/my-courses/                   — student's own registrations
"""

from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.mixins import ActionSerializerMixin
from core.permissions import HasModulePermission

from .models import (
    AssignmentReport,
    CourseAssessment,
    CourseLesson,
    CourseMessage,
    CourseModificationRequest,
    CourseProgress,
    CourseRegistration,
    LessonTopic,
    LiveSession,
    LiveSessionConsent,
    LiveSessionRequest,
    SessionContent,
    TopicSession,
    TrainingCategory,
    TrainingCourse,
)
from .serializers import (
    AssignmentReportSerializer,
    AssignmentSerializer,
    CourseAssessmentSerializer,
    CourseLessonSerializer,
    CourseMessageSerializer,
    CourseModificationRequestSerializer,
    CourseProgressSerializer,
    CourseRegistrationSerializer,
    InteractiveQuestionSerializer,
    LessonTopicSerializer,
    LiveSessionConsentSerializer,
    LiveSessionRequestSerializer,
    LiveSessionSerializer,
    SessionContentSerializer,
    TopicSessionSerializer,
    TrainingCategorySerializer,
    TrainingCourseListSerializer,
    TrainingCourseSerializer,
)


class HasTrainingPermission(HasModulePermission):
    module = "training"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
        "publish": "change",
        "lessons": "change",
        "live_sessions": "change",
        "assessments": "change",
        "completion_parameters": "change",
        "register": "add",
        "registrations": "view",
        "progress": "change",
        "my_courses": "view",
        "progress_summary": "view",
        "messages": "add",
        "assignment_reports": "add",
        "review_report": "change",
        "approve_late_submission": "change",
        "request_update": "change",
        "consent": "add",
        "consents": "view",
        "interactive_questions": "change",
        "notify_students": "change",
        "reschedule": "change",
        # CourseModificationRequestViewSet + LiveSessionRequestViewSet custom actions
        "approve": "change",
        "decline": "change",
        "zoom_config": "view",
        "zoom_create_meeting": "change",
        # Nested resource actions (CourseLessonViewSet, LessonTopicViewSet, etc.)
        "topics": "change",
        "sessions": "change",
        "contents": "change",
        "assignments": "change",
        # Also allow 'view' for GET on nested resources
        "categories": "view",
    }


def _next_order(queryset, field="order"):
    """Get the next order value for a new item in the queryset."""
    last = queryset.order_by(f"-{field}").first()
    return (getattr(last, field, -1) + 1) if last else 0


def _is_training_admin(user) -> bool:
    user_role_name = user.role.name if user.role_id else None
    return bool(user.is_superuser or user_role_name == "cj_admin")


def _require_course_edit_allowed(request, course):
    """Doc 7 §5: once a course leaves 'draft', a non-admin trainer must go
    through the existing request_update/CourseModificationRequest flow
    (POST /courses/<id>/request-update/) rather than mutating the course or
    its structure directly. cj_admin always bypasses this check.

    A trainer creating structure for the FIRST time (course still 'draft')
    is never gated. Once published/archived, a trainer may mutate again
    only if they hold an approved 'update' request that hasn't already
    been consumed by a prior edit (tracked via course.updated_at, since
    CourseModificationRequest carries no field-level diff to "apply").

    Returns a Response to short-circuit with if not allowed, else None.
    """
    user = request.user
    if _is_training_admin(user) or course.status == "draft":
        return None
    cur = (
        CourseModificationRequest.objects.filter(
            course=course, trainer=user, request_type="update", status="approved"
        )
        .order_by("-reviewed_at")
        .first()
    )
    if cur and cur.reviewed_at and cur.reviewed_at > course.updated_at:
        return None
    return Response(
        {
            "error": {
                "code": "approval_required",
                "message": (
                    "This course is published. Submit a course update request "
                    "(POST /courses/<id>/request-update/) and wait for admin "
                    "approval before editing its structure."
                ),
            }
        },
        status=status.HTTP_403_FORBIDDEN,
    )


# ---------------------------------------------------------------------------
# Category ViewSet
# ---------------------------------------------------------------------------


class TrainingCategoryViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for training categories (admin-managed)."""

    queryset = TrainingCategory.objects.all()
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = TrainingCategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Category created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Course ViewSet
# ---------------------------------------------------------------------------


class TrainingCourseViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for training courses + registration + progress endpoints."""

    queryset = TrainingCourse.objects.select_related("category", "created_by").prefetch_related(
        "lessons__topics__sessions__contents",
        "lessons__topics__sessions__assignments",
        "live_sessions",
        "assessments__assessment",
    )
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = TrainingCourseSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "objective", "description"]
    ordering_fields = ["created_at", "title", "status"]
    ordering = ["-created_at"]
    serializer_classes = {
        "list": TrainingCourseListSerializer,
    }

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if status_filter := params.get("status"):
            qs = qs.filter(status=status_filter)
        if category := params.get("category"):
            qs = qs.filter(category_id=category)
        if course_type := params.get("course_type"):
            qs = qs.filter(course_type=course_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Course created.",
                "data": TrainingCourseSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """Override to return wrapped envelope (matching create/retrieve)."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        denied = _require_course_edit_allowed(request, instance)
        if denied:
            return denied
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Course updated.", "data": TrainingCourseSerializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        """Per SRS §5: 'Deleting a course is the right of Admin only'."""
        user_role_name = request.user.role.name if request.user.role_id else None
        is_admin = user_role_name == "cj_admin"
        if not is_admin:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only CJ Admin can delete a training course (SRS §5).",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a draft course so students can register."""
        course = self.get_object()
        if course.status != "draft":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Course must be in 'draft' status. Current: '{course.status}'",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        course.status = "published"
        course.save(update_fields=["status", "updated_at"])
        return Response(
            {"message": "Course published.", "data": {"id": course.id, "status": course.status}},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"])
    def lessons(self, request, pk=None):
        """List or add lessons to a course (SRS §2.2).

        Per SRS §5: course structure modification is admin-only. Trainers
        can view but not create/modify lessons, topics, or sessions.
        """
        course = self.get_object()
        if request.method == "GET":
            lessons = course.lessons.all()
            return Response(
                {"message": "OK", "data": CourseLessonSerializer(lessons, many=True).data},
                status=status.HTTP_200_OK,
            )
        # POST: admin-only (SRS §5)
        user_role_name = request.user.role.name if request.user.role_id else None
        if user_role_name != "cj_admin":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": (
                            "Course structure can only be modified by CJ Admin (SRS §5). "
                            "Trainers may modify assignments and main session contents only."
                        ),
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CourseLessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course, order=_next_order(course.lessons))
        return Response(
            {"message": "Lesson created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def live_sessions(self, request, pk=None):
        """List or add live sessions (SRS §2.5)."""
        course = self.get_object()
        if request.method == "GET":
            sessions = course.live_sessions.all()
            return Response(
                {"message": "OK", "data": LiveSessionSerializer(sessions, many=True).data},
                status=status.HTTP_200_OK,
            )
        serializer = LiveSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course)
        return Response(
            {"message": "Live session created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def assessments(self, request, pk=None):
        """List or add course assessments (SRS §2.4)."""
        course = self.get_object()
        if request.method == "GET":
            assessments = course.assessments.all()
            return Response(
                {"message": "OK", "data": CourseAssessmentSerializer(assessments, many=True).data},
                status=status.HTTP_200_OK,
            )
        serializer = CourseAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course)
        return Response(
            {"message": "Assessment added.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"], url_path="completion-parameters")
    def completion_parameters(self, request, pk=None):
        """Report 3 §6.1: list or set course-completion parameters.

        GET: returns all CourseCompletionParameter rows for this course.
        POST body (set/replace the full set):
            {
              "parameters": [
                {"content_type": "session_content", "content_id": 12, "is_mandatory": true},
                {"content_type": "assignment",      "content_id": 7,  "is_mandatory": true},
                ...
              ]
            }
        Posting replaces the full set (idempotent) so the trainer's 'Set
        Parameters' form reflects exactly what they checked.
        """
        from .models import CourseCompletionParameter
        from .serializers import CourseCompletionParameterSerializer

        course = self.get_object()
        if request.method == "GET":
            params = course.completion_parameters.all()
            return Response(
                {
                    "message": "OK",
                    "data": CourseCompletionParameterSerializer(params, many=True).data,
                },
                status=status.HTTP_200_OK,
            )
        # POST: replace the full set
        parameters = request.data.get("parameters", [])
        if not isinstance(parameters, list):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "parameters must be a list.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        CourseCompletionParameter.objects.filter(course=course).delete()
        new_objs = [
            CourseCompletionParameter(
                course=course,
                content_type=p.get("content_type"),
                content_id=p.get("content_id"),
                is_mandatory=bool(p.get("is_mandatory", True)),
            )
            for p in parameters
            if p.get("content_type") and p.get("content_id")
        ]
        CourseCompletionParameter.objects.bulk_create(new_objs)
        return Response(
            {
                "message": f"Saved {len(new_objs)} completion parameter(s).",
                "data": CourseCompletionParameterSerializer(
                    course.completion_parameters.all(), many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def register(self, request, pk=None):
        """Student registers for a course (SRS §6 + Report 3 §1).

        Captures a registration form (prefilled from the user's profile +
        any extra answers in the request body), creates a CourseRegistration,
        and creates a Payment record. For free courses (price=0) payment is
        auto-completed and the course commences immediately. For paid courses
        a Stripe Checkout session is created and its URL returned so the
        frontend can redirect; the webhook flips payment_status to 'paid'
        (payments/services._update_module_payment_status).

        Per SRS §6: for scheduled courses, started_at is set when payment
        completes (so the duration countdown begins then).
        """
        from django.utils import timezone

        from apps.payments.services import create_stripe_checkout_session, get_or_create_payment

        course = self.get_object()
        if course.status != "published":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Course must be published before students can register.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Build the registration-form snapshot: profile fields + any extra
        # answers the candidate provided in the request body (Report 3 §1.1).
        profile = getattr(request.user, "profile", None)
        registration_form = {
            "full_name": request.user.full_name,
            "email": request.user.email,
            "phone": getattr(profile, "phone", "") if profile else "",
            "extra_answers": request.data.get("extra_answers", {}),
        }

        # Free courses (price == 0) are auto-paid — no payment gateway needed
        is_free = float(course.price) == 0
        payment_status = "paid" if is_free else "pending"
        completion_status = "in_progress" if is_free else "not_started"

        reg, created = CourseRegistration.objects.get_or_create(
            course=course,
            student=request.user,
            defaults={
                "payment_status": payment_status,
                "completion_status": completion_status,
                "registration_form": registration_form,
                # For scheduled courses the duration countdown begins at
                # registration when free, or when payment completes when paid
                # (set in payments/services._update_module_payment_status).
                "started_at": (
                    timezone.now() if (is_free and course.schedule_type == "scheduled") else None
                ),
            },
        )
        if not created:
            return Response(
                {
                    "message": "Already registered for this course.",
                    "data": CourseRegistrationSerializer(reg).data,
                },
                status=status.HTTP_200_OK,
            )

        # Create a Payment record + (for paid courses) a Stripe Checkout URL.
        payment = get_or_create_payment(
            request.user,
            module="training",
            item_id=course.id,
            amount=course.price,
            description=f"Registration: {course.title}",
        )
        checkout_url = None
        if not is_free:
            success_url = request.build_absolute_uri("/training/my-courses/?payment=success")
            cancel_url = request.build_absolute_uri("/training/?payment=cancelled")
            checkout_url = create_stripe_checkout_session(payment, success_url, cancel_url)

        message = (
            "Registration created. You can start the course now."
            if is_free
            else (
                "Registration created. Complete payment to start the course."
                if checkout_url is None
                else "Registration created. Redirecting to payment…"
            )
        )
        return Response(
            {
                "message": message,
                "data": {
                    **CourseRegistrationSerializer(reg).data,
                    "checkout_url": checkout_url,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def registrations(self, request, pk=None):
        """Trainer views all registrations for a course."""
        course = self.get_object()
        regs = course.registrations.select_related("student").all()
        return Response(
            {"message": "OK", "data": CourseRegistrationSerializer(regs, many=True).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def my_courses(self, request):
        """Student views their own registrations."""
        regs = (
            CourseRegistration.objects.filter(student=request.user)
            .select_related("course", "student")
            .order_by("-registered_at")
        )
        return Response(
            {"message": "OK", "data": CourseRegistrationSerializer(regs, many=True).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="request-update")
    def request_update(self, request, pk=None):
        """Report 3 §7.1/§7.2: trainer requests admin approval to update or
        delete a PUBLISHED course.

        POST body: {"request_type": "update" | "delete", "reason": "..."}
        Creates a pending CourseModificationRequest and notifies cj_admin. Only the
        course's trainer (or admin) may request. The admin approves/declines
        via the CourseModificationRequestViewSet.
        """
        course = self.get_object()
        user = request.user
        user_role_name = user.role.name if user.role_id else None
        is_trainer_or_admin = course.created_by_id == user.id or user_role_name == "cj_admin"
        if not is_trainer_or_admin:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the course trainer or admin can request changes.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        req_type = request.data.get("request_type")
        if req_type not in ("update", "delete"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "request_type must be 'update' or 'delete'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            return Response(
                {"error": {"code": "validation_error", "message": "reason is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cur = CourseModificationRequest.objects.create(
            course=course,
            trainer=user,
            request_type=req_type,
            reason=reason,
        )
        return Response(
            {
                "message": "Request submitted. An admin will review it.",
                "data": CourseModificationRequestSerializer(cur).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def zoom_config(self, request):
        """Check if Zoom API is configured (for auto-create meeting feature).

        Returns { is_configured: bool }. If true, the frontend shows an
        'Auto-create Zoom Meeting' option in the Live Session form. If false,
        the form falls back to manual URL entry.
        """
        from .zoom import is_zoom_configured

        return Response(
            {"message": "OK", "data": {"is_configured": is_zoom_configured()}},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def zoom_create_meeting(self, request):
        """Create a Zoom meeting via the API (requires Zoom credentials in env).

        Body:
            { "topic": "Q&A Session", "start_time": "2026-08-01T10:00:00Z",
              "duration_minutes": 60 }

        Returns:
            { "join_url": "https://zoom.us/j/...", "meeting_id": "123", "password": "abc" }
            or 400 if Zoom is not configured.
        """
        from .zoom import create_zoom_meeting, is_zoom_configured

        if not is_zoom_configured():
            return Response(
                {
                    "error": {
                        "code": "not_configured",
                        "message": (
                            "Zoom API is not configured. Set ZOOM_ACCOUNT_ID, "
                            "ZOOM_CLIENT_ID, and ZOOM_CLIENT_SECRET environment "
                            "variables to enable auto-create. Alternatively, "
                            "enter the meeting URL manually."
                        ),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        topic = request.data.get("topic", "Training Session")
        start_time = request.data.get("start_time")
        duration = int(request.data.get("duration_minutes", 60))

        if not start_time:
            return Response(
                {"error": {"code": "validation_error", "message": "start_time is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = create_zoom_meeting(topic, start_time, duration)
        if result:
            return Response(
                {"message": "Zoom meeting created.", "data": result},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "error": {
                    "code": "zoom_error",
                    "message": "Failed to create Zoom meeting. Check server logs.",
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Registration ViewSet (for progress tracking)
# ---------------------------------------------------------------------------


class CourseRegistrationViewSet(ModelViewSet):
    """Retrieve registrations + track progress."""

    queryset = CourseRegistration.objects.select_related("course", "student")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = CourseRegistrationSerializer
    # POST is allowed for the 'progress' action (upsert). The base
    # registration create happens via /courses/<id>/register/ instead.
    http_method_names = ["get", "head", "options", "patch", "post"]

    def get_queryset(self):
        # Students see only their own registrations; trainers/admins see all
        user = self.request.user
        user_role_name = user.role.name if user.role_id else None
        if user_role_name in ("cj_admin", "trainer"):
            return super().get_queryset()
        return super().get_queryset().filter(student=user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"])
    def progress(self, request, pk=None):
        """List or update progress records for a registration (SRS §6).

        POST body:
            {
                "content_type": "session_content" | "assignment" | ...,
                "content_id": 42,
                "is_completed": true,
                "time_spent_seconds": 120
            }
        """
        reg = self.get_object()
        if request.method == "GET":
            progress = reg.progress_records.all()
            return Response(
                {"message": "OK", "data": CourseProgressSerializer(progress, many=True).data},
                status=status.HTTP_200_OK,
            )
        # POST: upsert the progress record
        content_type = request.data.get("content_type")
        content_id = request.data.get("content_id")
        if not content_type or not content_id:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "content_type and content_id are required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone

        progress, _ = CourseProgress.objects.update_or_create(
            registration=reg,
            content_type=content_type,
            content_id=content_id,
            defaults={
                "is_completed": bool(request.data.get("is_completed", False)),
                "time_spent_seconds": int(request.data.get("time_spent_seconds", 0)),
                "last_accessed_at": timezone.now(),
            },
        )
        return Response(
            {"message": "Progress updated.", "data": CourseProgressSerializer(progress).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def progress_summary(self, request, pk=None):
        """Aggregated progress for a registration (SRS §6: 'Course Completion
        Status, Time Tracker, Score report, Option to resume from where
        last left').

        Returns:
            {
                "completion_percentage": 65.0,
                "total_time_spent_seconds": 7200,
                "total_time_allowed_seconds": 864000,  # null for non-scheduled
                "time_left_seconds": 856800,
                "completed_count": 13,
                "total_count": 20,
                "last_accessed_at": "2026-07-20T...",
                "last_content": {"content_type": "session_content", "content_id": 42},
                "completion_status": "in_progress",
                "started_at": "2026-07-15T...",
                "is_expired": false
            }
        """
        reg = self.get_object()
        progress_records = list(reg.progress_records.all())
        completed = [p for p in progress_records if p.is_completed]
        total_time_spent = sum(p.time_spent_seconds for p in progress_records)
        last_accessed = max(
            (p.last_accessed_at for p in progress_records if p.last_accessed_at),
            default=None,
        )
        # Find the last content the student accessed (for resume)
        last_content = None
        if progress_records:
            last_record = max(
                progress_records,
                key=lambda p: p.last_accessed_at or reg.registered_at,
            )
            last_content = {
                "content_type": last_record.content_type,
                "content_id": last_record.content_id,
            }

        # Time tracking for scheduled courses

        from django.utils import timezone

        total_time_allowed = None
        time_left = None
        is_expired = False
        if reg.course.schedule_type == "scheduled" and reg.course.duration_days:
            total_time_allowed = reg.course.duration_days * 86400
            if reg.started_at:
                elapsed = (timezone.now() - reg.started_at).total_seconds()
                time_left = max(0, total_time_allowed - int(elapsed))
                is_expired = time_left == 0

        completion_pct = (
            round((len(completed) / len(progress_records)) * 100, 1) if progress_records else 0.0
        )

        # Report 3 §6: completion against MANDATORY parameters. If the trainer
        # has marked any contents mandatory, compute what fraction of those
        # mandatory contents the student has completed (this is the figure that
        # determines true course completion). Falls back to completion_pct when
        # no mandatory params are set.
        mandatory_params = list(reg.course.completion_parameters.filter(is_mandatory=True))
        mandatory_completion_pct = None
        mandatory_completed_count = None
        mandatory_total_count = None
        if mandatory_params:
            completed_keys = {
                (p.content_type, p.content_id) for p in progress_records if p.is_completed
            }
            mandatory_total_count = len(mandatory_params)
            mandatory_completed_count = sum(
                1 for mp in mandatory_params if (mp.content_type, mp.content_id) in completed_keys
            )
            mandatory_completion_pct = (
                round((mandatory_completed_count / mandatory_total_count) * 100, 1)
                if mandatory_total_count
                else 0.0
            )
            # Override completion_pct with the mandatory figure when set — this
            # is what 'course completion' actually means per SRS §2.6.
            completion_pct = mandatory_completion_pct

        # Dossier gap D7: roll assessment + report scores into the progress
        # summary (SRS §6: "Course Completion Status, Time Tracker, Score
        # report, Option to resume from where last left").
        #
        #   - assessment_scores: the student's latest completed
        #     AssessmentSession percentage for each CourseAssessment attached
        #     to this course.
        #   - assignment_report_scores: the trainer's score/rating (out of 10)
        #     on each of the student's reviewed AssignmentReport submissions
        #     — the "Score report" half of SRS §6.
        from apps.assessment.models import AssessmentSession

        assessment_scores = []
        percentages = []
        for ca in reg.course.assessments.select_related("assessment").all():
            latest = (
                AssessmentSession.objects.filter(
                    assessment_id=ca.assessment_id, candidate=reg.student, status="completed"
                )
                .order_by("-completed_at")
                .first()
            )
            assessment_scores.append(
                {
                    "course_assessment_id": ca.id,
                    "title": ca.title,
                    "level": ca.level,
                    "assessment_id": ca.assessment_id,
                    "session_id": latest.id if latest else None,
                    "percentage": latest.percentage if latest else None,
                    "total_score": latest.total_score if latest else None,
                    "max_score": latest.max_score if latest else None,
                    "status": "completed" if latest else "not_attempted",
                }
            )
            if latest and latest.percentage is not None:
                percentages.append(latest.percentage)

        assignment_report_scores = [
            {
                "assignment_id": ar.assignment_id,
                "assignment_title": ar.assignment.title,
                "status": ar.status,
                "trainer_score": ar.trainer_score,
            }
            for ar in AssignmentReport.objects.filter(
                assignment__session__topic__lesson__course=reg.course, student=reg.student
            ).select_related("assignment")
        ]

        return Response(
            {
                "message": "OK",
                "data": {
                    "completion_percentage": completion_pct,
                    "completed_count": len(completed),
                    "total_count": len(progress_records),
                    "mandatory_completion_percentage": mandatory_completion_pct,
                    "mandatory_completed_count": mandatory_completed_count,
                    "mandatory_total_count": mandatory_total_count,
                    "total_time_spent_seconds": total_time_spent,
                    "total_time_allowed_seconds": total_time_allowed,
                    "time_left_seconds": time_left,
                    "is_expired": is_expired,
                    "last_accessed_at": last_accessed.isoformat() if last_accessed else None,
                    "last_content": last_content,
                    "completion_status": reg.completion_status,
                    "started_at": reg.started_at.isoformat() if reg.started_at else None,
                    "assessment_scores": assessment_scores,
                    "average_assessment_percentage": (
                        round(sum(percentages) / len(percentages), 1) if percentages else None
                    ),
                    "assignment_report_scores": assignment_report_scores,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        """List or send messages for a registration (SRS §5: 'Check messages
        from end-users and respond').

        POST body: {"body": "message text"}
        The sender is the authenticated user. The recipient is inferred:
          - if sender is the student -> recipient is the course's trainer
          - if sender is the trainer -> recipient is the student
        """
        reg = self.get_object()
        if request.method == "GET":
            messages = reg.messages.select_related("sender").all()
            return Response(
                {"message": "OK", "data": CourseMessageSerializer(messages, many=True).data},
                status=status.HTTP_200_OK,
            )
        # POST: send a message
        body = request.data.get("body", "").strip()
        if not body:
            return Response(
                {"error": {"code": "validation_error", "message": "body is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Validate sender is either the student or the course trainer
        user = request.user
        is_student = reg.student_id == user.id
        is_trainer = reg.course.created_by_id == user.id
        user_role_name = user.role.name if user.role_id else None
        is_admin = user_role_name == "cj_admin"
        if not (is_student or is_trainer or is_admin):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the registered student, course trainer, or admin can send messages.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        msg = CourseMessage.objects.create(
            registration=reg,
            sender=user,
            body=body,
        )
        return Response(
            {"message": "Message sent.", "data": CourseMessageSerializer(msg).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def assignment_reports(self, request, pk=None):
        """List or submit assignment reports for a registration (SRS §2.3.2).

        GET: trainer views all reports for this registration
        POST: student submits a report for an assignment
            body: {"assignment": 42, "report_text": "...", "report_file_url": "..."}

        Per SRS §2.3.2 rule: when a student submits, a notification is
        sent to the trainer (notification wired via signals).
        """
        reg = self.get_object()
        if request.method == "GET":
            # Trainer/admin can view all reports; student views only their own
            user = request.user
            user_role_name = user.role.name if user.role_id else None
            is_trainer_or_admin = (
                reg.course.created_by_id == user.id or user_role_name == "cj_admin"
            )
            if not is_trainer_or_admin and reg.student_id != user.id:
                return Response(
                    {"error": {"code": "forbidden", "message": "Not authorized."}},
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Get all reports for assignments in this course where the student matches
            reports = AssignmentReport.objects.filter(
                student=reg.student,
                assignment__session__topic__lesson__course=reg.course,
            ).select_related("student", "assignment", "reviewed_by")
            return Response(
                {"message": "OK", "data": AssignmentReportSerializer(reports, many=True).data},
                status=status.HTTP_200_OK,
            )
        # POST: student submits a report
        if reg.student_id != request.user.id:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the registered student can submit reports.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        assignment_id = request.data.get("assignment")
        if not assignment_id:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "assignment (ID) is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import Assignment

        assignment = Assignment.objects.filter(
            id=assignment_id,
            session__topic__lesson__course=reg.course,
            report_submission_enabled=True,
        ).first()
        if not assignment:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Assignment not found or report submission not enabled.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Report 3 §3.3: enforce submission deadline. After the deadline,
        # submission requires trainer approval (late_submission_approved).
        from django.utils import timezone

        existing = AssignmentReport.objects.filter(
            assignment=assignment, student=request.user
        ).first()
        deadline_passed = (
            assignment.submission_deadline is not None
            and assignment.submission_deadline < timezone.now()
        )
        late_ok = bool(existing and existing.late_submission_approved)
        if deadline_passed and not late_ok:
            return Response(
                {
                    "error": {
                        "code": "deadline_passed",
                        "message": (
                            "The submission deadline for this assignment has passed. "
                            "Ask the trainer to approve a late submission."
                        ),
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Report 3 §3.6: accept an uploaded file (multipart) OR a URL.
        report_file = request.data.get("report_file")
        report, created = AssignmentReport.objects.update_or_create(
            assignment=assignment,
            student=request.user,
            defaults={
                "report_text": request.data.get("report_text", ""),
                "report_file_url": request.data.get("report_file_url", ""),
                "report_file": (
                    report_file if report_file else (existing.report_file if existing else None)
                ),
                "status": "submitted",
                # A new submission resets the late-approval flag.
                "late_submission_approved": False,
            },
        )

        return Response(
            {"message": "Report submitted.", "data": AssignmentReportSerializer(report).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="review-report")
    def review_report(self, request, pk=None):
        """Trainer reviews an assignment report (SRS §2.3.2 + §5).

        POST body: {"report_id": 42, "trainer_score": 85, "trainer_feedback": "Good work"}
        Sets the report status to 'reviewed' and records the trainer + timestamp.
        """
        reg = self.get_object()
        user = request.user
        user_role_name = user.role.name if user.role_id else None
        is_trainer_or_admin = reg.course.created_by_id == user.id or user_role_name == "cj_admin"
        if not is_trainer_or_admin:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the course trainer or admin can review reports.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        report_id = request.data.get("report_id")
        report = AssignmentReport.objects.filter(
            id=report_id,
            student=reg.student,
            assignment__session__topic__lesson__course=reg.course,
        ).first()
        if not report:
            return Response(
                {"error": {"code": "not_found", "message": "Report not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Report 3 §3.8: trainer rates on a 0-10 scale.
        trainer_score = request.data.get("trainer_score")
        if trainer_score is not None:
            try:
                trainer_score = float(trainer_score)
            except (TypeError, ValueError):
                trainer_score = None
            if trainer_score is not None and not (0 <= trainer_score <= 10):
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": "trainer_score must be between 0 and 10.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        from django.utils import timezone

        report.trainer_score = trainer_score
        report.trainer_feedback = request.data.get("trainer_feedback", "")
        report.reviewed_by = user
        report.reviewed_at = timezone.now()
        report.status = "reviewed"
        report.save()
        # Report 3 §3.8: notify the student that their report was reviewed.
        try:
            from apps.notifications.models import notify_user

            score_str = f"{trainer_score:g}/10" if trainer_score is not None else "—"
            notify_user(
                reg.student,
                f"Report reviewed: {report.assignment.title}",
                f"Your report for '{report.assignment.title}' was reviewed. "
                f"Score: {score_str}.",
                "session",
                f"/training/{reg.course_id}",
            )
        except Exception:
            pass
        return Response(
            {"message": "Report reviewed.", "data": AssignmentReportSerializer(report).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="approve-late-submission")
    def approve_late_submission(self, request, pk=None):
        """Trainer approves a late assignment submission after the deadline
        has passed (Report 3 §3.3).

        POST body: {"report_id": 42}  (report must already exist)
        """
        reg = self.get_object()
        user = request.user
        user_role_name = user.role.name if user.role_id else None
        is_trainer_or_admin = reg.course.created_by_id == user.id or user_role_name == "cj_admin"
        if not is_trainer_or_admin:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the course trainer or admin can approve late submissions.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        report_id = request.data.get("report_id")
        report = AssignmentReport.objects.filter(
            id=report_id,
            student=reg.student,
            assignment__session__topic__lesson__course=reg.course,
        ).first()
        if not report:
            return Response(
                {"error": {"code": "not_found", "message": "Report not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        report.late_submission_approved = True
        report.save(update_fields=["late_submission_approved"])
        # Notify the student they can now submit.
        try:
            from apps.notifications.models import notify_user

            notify_user(
                reg.student,
                f"Late submission approved: {report.assignment.title}",
                "Your trainer has approved a late submission. You can now submit your report.",
                "session",
                f"/training/{reg.course_id}",
            )
        except Exception:
            pass
        return Response(
            {
                "message": "Late submission approved.",
                "data": AssignmentReportSerializer(report).data,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Nested resource ViewSets (lessons/topics/sessions/contents/assignments)
# ---------------------------------------------------------------------------


class _CourseStructureEditGuardMixin:
    """TRN-1 / Doc 7 §5: gate the default update/partial_update/destroy on the
    nested course-structure viewsets through the same published-course approval
    flow as their create actions — so a trainer cannot directly edit or delete a
    published course's lesson/topic/session/content/assessment structure. Admins
    and still-draft courses bypass (see _require_course_edit_allowed).
    Subclasses implement _course_for(obj)."""

    def _course_for(self, obj):  # pragma: no cover - overridden
        raise NotImplementedError

    def _guard_structure_edit(self, request):
        return _require_course_edit_allowed(request, self._course_for(self.get_object()))

    def update(self, request, *args, **kwargs):
        denied = self._guard_structure_edit(request)
        if denied:
            return denied
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        denied = self._guard_structure_edit(request)
        if denied:
            return denied
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        denied = self._guard_structure_edit(request)
        if denied:
            return denied
        return super().destroy(request, *args, **kwargs)


class CourseLessonViewSet(_CourseStructureEditGuardMixin, ModelViewSet):
    """CRUD for lessons within a course."""

    queryset = CourseLesson.objects.select_related("course")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = CourseLessonSerializer

    def _course_for(self, obj):
        return obj.course

    @action(detail=True, methods=["get", "post"])
    def topics(self, request, pk=None):
        """List or add topics to a lesson (SRS §2.2)."""
        lesson = self.get_object()
        if request.method == "GET":
            topics = lesson.topics.all()
            return Response(
                {"message": "OK", "data": LessonTopicSerializer(topics, many=True).data},
                status=status.HTTP_200_OK,
            )
        denied = _require_course_edit_allowed(request, lesson.course)
        if denied:
            return denied
        serializer = LessonTopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lesson=lesson, order=_next_order(lesson.topics))
        # Consume the approval used above, if any, by touching the parent
        # course's updated_at (see _require_course_edit_allowed).
        lesson.course.save(update_fields=["updated_at"])
        return Response(
            {"message": "Topic created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class LessonTopicViewSet(_CourseStructureEditGuardMixin, ModelViewSet):
    """CRUD for topics within a lesson."""

    queryset = LessonTopic.objects.select_related("lesson")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = LessonTopicSerializer

    def _course_for(self, obj):
        return obj.lesson.course

    @action(detail=True, methods=["get", "post"])
    def sessions(self, request, pk=None):
        """List or add sessions to a topic (SRS §2.2)."""
        topic = self.get_object()
        if request.method == "GET":
            sessions = topic.sessions.all()
            return Response(
                {"message": "OK", "data": TopicSessionSerializer(sessions, many=True).data},
                status=status.HTTP_200_OK,
            )
        course = topic.lesson.course
        denied = _require_course_edit_allowed(request, course)
        if denied:
            return denied
        serializer = TopicSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(topic=topic, order=_next_order(topic.sessions))
        course.save(update_fields=["updated_at"])
        return Response(
            {"message": "Session created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class TopicSessionViewSet(_CourseStructureEditGuardMixin, ModelViewSet):
    """CRUD for sessions within a topic."""

    queryset = TopicSession.objects.select_related("topic")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = TopicSessionSerializer

    def _course_for(self, obj):
        return obj.topic.lesson.course

    @action(detail=True, methods=["get", "post"])
    def contents(self, request, pk=None):
        """List or add content to a session (SRS §2.3.1)."""
        session = self.get_object()
        if request.method == "GET":
            contents = session.contents.all()
            return Response(
                {"message": "OK", "data": SessionContentSerializer(contents, many=True).data},
                status=status.HTTP_200_OK,
            )
        course = session.topic.lesson.course
        denied = _require_course_edit_allowed(request, course)
        if denied:
            return denied
        serializer = SessionContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session, order=_next_order(session.contents))
        course.save(update_fields=["updated_at"])
        return Response(
            {"message": "Content created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def assignments(self, request, pk=None):
        """List or add assignments to a session (SRS §2.3.2)."""
        session = self.get_object()
        if request.method == "GET":
            assignments = session.assignments.all()
            return Response(
                {"message": "OK", "data": AssignmentSerializer(assignments, many=True).data},
                status=status.HTTP_200_OK,
            )
        course = session.topic.lesson.course
        denied = _require_course_edit_allowed(request, course)
        if denied:
            return denied
        serializer = AssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session, order=_next_order(session.assignments))
        course.save(update_fields=["updated_at"])
        return Response(
            {"message": "Assignment created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Live Session ViewSet (consent + notify — SRS §5)
# ---------------------------------------------------------------------------


class LiveSessionViewSet(ModelViewSet):
    """CRUD for live sessions + consent tracking (SRS §5).

    Per SRS §5 scheduler_process: trainer schedules a Zoom/classroom
    session, students get notified, students click 'Consent', trainer
    sees who's attending.
    """

    queryset = LiveSession.objects.select_related("course", "course__created_by")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = LiveSessionSerializer
    http_method_names = ["get", "head", "options", "patch", "post"]

    @action(detail=True, methods=["post"])
    def consent(self, request, pk=None):
        """Student consents or declines to attend a live session (SRS §5).

        POST /api/training/live-sessions/<id>/consent/
        body: {"status": "consented" | "rejected"}

        Creates a LiveSessionConsent record. A notification is sent to the
        trainer via the post_save signal (apps/training/signals.py).
        """
        live_session = self.get_object()
        status_val = request.data.get("status", "consented")
        # Accept the canonical "declined" plus remote's legacy "rejected"
        # spelling; always store the canonical model choice.
        if status_val == "rejected":
            status_val = "declined"
        if status_val not in ("consented", "declined"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "status must be 'consented' or 'declined'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        consent, _ = LiveSessionConsent.objects.update_or_create(
            live_session=live_session,
            student=request.user,
            defaults={"status": status_val},
        )
        return Response(
            {
                "message": f"You have {status_val} to this session.",
                "data": LiveSessionConsentSerializer(consent).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def consents(self, request, pk=None):
        """Trainer views the consent list for a live session (SRS §5)."""
        live_session = self.get_object()
        # Only the course trainer or admin can view consents
        user_role_name = request.user.role.name if request.user.role_id else None
        is_trainer_or_admin = (
            live_session.course.created_by_id == request.user.id or user_role_name == "cj_admin"
        )
        if not is_trainer_or_admin:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the trainer or admin can view consents.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        consents = live_session.consents.select_related("student").all()
        return Response(
            {"message": "OK", "data": LiveSessionConsentSerializer(consents, many=True).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def notify_students(self, request, pk=None):
        """Trainer manually triggers a notification to all registered students
        about an upcoming live session (SRS §5).

        This is useful for reminding students about an existing session
        (the automatic signal only fires on creation).
        """
        from apps.notifications.models import notify_user

        live_session = self.get_object()
        user_role_name = request.user.role.name if request.user.role_id else None
        is_trainer_or_admin = (
            live_session.course.created_by_id == request.user.id or user_role_name == "cj_admin"
        )
        if not is_trainer_or_admin:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the trainer or admin can notify students.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        regs = CourseRegistration.objects.filter(
            course=live_session.course, payment_status="paid"
        ).select_related("student")
        scheduled_str = live_session.scheduled_at.strftime("%Y-%m-%d %H:%M")
        count = 0
        for reg in regs:
            notify_user(
                reg.student,
                f"Live session reminder: {live_session.title}",
                f"Starting on {scheduled_str}. Duration: {live_session.duration_minutes} min. "
                f"Mode: {live_session.mode}.",
                "session",
                f"/training/{live_session.course_id}?live_session={live_session.id}",
            )
            count += 1
        return Response(
            {"message": f"Notified {count} student(s).", "data": {"notified_count": count}},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reschedule")
    def reschedule(self, request, pk=None):
        """Report 3 §7.4/OL.2: trainer reschedules a session to a new time.

        POST body: {"scheduled_at": "2026-08-10T10:00:00Z", "reason": "..."}
        Records the previous time in rescheduled_from + the reason, then
        notifies all registered students.
        """
        live_session = self.get_object()
        user_role_name = request.user.role.name if request.user.role_id else None
        is_trainer_or_admin = (
            live_session.course.created_by_id == request.user.id or user_role_name == "cj_admin"
        )
        if not is_trainer_or_admin:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the trainer or admin can reschedule a session.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        new_time = request.data.get("scheduled_at")
        reason = (request.data.get("reason") or "").strip()
        if not new_time:
            return Response(
                {"error": {"code": "validation_error", "message": "scheduled_at is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not reason:
            return Response(
                {"error": {"code": "validation_error", "message": "reason is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone

        # Parse + record the previous time.
        try:
            from datetime import datetime

            parsed = datetime.fromisoformat(str(new_time).replace("Z", "+00:00"))
        except ValueError:
            return Response(
                {"error": {"code": "validation_error", "message": "Invalid scheduled_at format."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        live_session.rescheduled_from = live_session.scheduled_at
        live_session.reschedule_reason = reason
        live_session.scheduled_at = (
            parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
        )
        live_session.save(update_fields=["scheduled_at", "rescheduled_from", "reschedule_reason"])
        # Notify registered students.
        from apps.notifications.models import notify_user

        regs = CourseRegistration.objects.filter(
            course=live_session.course, payment_status="paid"
        ).select_related("student")
        new_str = live_session.scheduled_at.strftime("%Y-%m-%d %H:%M")
        for reg in regs:
            notify_user(
                reg.student,
                f"Session rescheduled: {live_session.title}",
                f"Moved to {new_str}. Reason: {reason}.",
                "session",
                f"/training/{live_session.course_id}?live_session={live_session.id}",
            )
        return Response(
            {"message": "Session rescheduled.", "data": LiveSessionSerializer(live_session).data},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Session Content → Interactive Questions (SRS §2.3.1 Timeliner)
# ---------------------------------------------------------------------------


class SessionContentViewSet(_CourseStructureEditGuardMixin, ModelViewSet):
    """CRUD for session content + interactive questions (Timeliner)."""

    queryset = SessionContent.objects.select_related("session")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = SessionContentSerializer

    def _course_for(self, obj):
        return obj.session.topic.lesson.course

    @action(detail=True, methods=["get", "post"])
    def interactive_questions(self, request, pk=None):
        """List or add interactive questions to a session content (SRS §2.3.1).

        GET /api/training/contents/<id>/interactive_questions/
          -> list of questions ordered by trigger_timestamp

        POST /api/training/contents/<id>/interactive_questions/
          body: {
            "question_text": "What is 2+2?",
            "trigger_timestamp": 30.5,
            "options": [
              {"id": 1, "text": "3", "is_correct": false},
              {"id": 2, "text": "4", "is_correct": true},
              {"id": 3, "text": "5", "is_correct": false}
            ],
            "correct_jump_to": 60.0,
            "incorrect_jump_to": 15.0
          }
        """
        content = self.get_object()
        if request.method == "GET":
            questions = content.interactive_questions.all()
            return Response(
                {"message": "OK", "data": InteractiveQuestionSerializer(questions, many=True).data},
                status=status.HTTP_200_OK,
            )
        serializer = InteractiveQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session_content=content)
        return Response(
            {"message": "Interactive question created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Course Assessment ViewSet (edit/delete linked assessments — SRS §2.4)
# ---------------------------------------------------------------------------


class CourseAssessmentViewSet(_CourseStructureEditGuardMixin, ModelViewSet):
    """CRUD for course assessments (SRS §2.4).

    Allows trainers to update and delete linked assessments, not just
    add them.
    """

    queryset = CourseAssessment.objects.select_related("course", "assessment", "session")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = CourseAssessmentSerializer
    http_method_names = ["get", "head", "options", "patch", "delete", "post"]

    def _course_for(self, obj):
        return obj.course


# ---------------------------------------------------------------------------
# Course Update Request (Report 3 §7.1/§7.2) — admin approval workflow
# ---------------------------------------------------------------------------


class CourseModificationRequestViewSet(ModelViewSet):
    """List/course-update requests + admin approve/decline actions.

    Trainers see their own requests; admins see all. Approve/decline are
    admin-only and notify the requesting trainer.
    """

    queryset = CourseModificationRequest.objects.select_related("course", "trainer", "reviewed_by")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = CourseModificationRequestSerializer
    http_method_names = ["get", "head", "options", "post"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        user_role_name = user.role.name if user.role_id else None
        if user_role_name == "cj_admin" or user.is_superuser:
            return qs
        # Trainers see only their own requests
        return qs.filter(trainer=user)

    def list(self, request, *args, **kwargs):
        # Serialize directly (NOT super().list()) so pagination cannot wrap
        # the payload into {count, results} — the frontend expects an array.
        qs = self.filter_queryset(self.get_queryset())
        return Response(
            {"message": "OK", "data": self.get_serializer(qs, many=True).data},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        # Creation happens via /courses/<id>/request-update/ (which scopes to
        # the course). Block direct creation here to keep the audit trail clean.
        return Response(
            {
                "error": {
                    "code": "forbidden",
                    "message": "Submit requests via POST /courses/<id>/request-update/.",
                }
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Admin approves a course update/delete request (Report 3 §7.1/§7.2)."""
        cur = self.get_object()
        user = request.user
        user_role_name = user.role.name if user.role_id else None
        if user_role_name != "cj_admin" and not user.is_superuser:
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can approve."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if cur.status != "pending":
            return Response(
                {
                    "error": {
                        "code": "invalid_state",
                        "message": f"Request is already {cur.status}.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone

        cur.status = "approved"
        cur.reviewed_by = user
        cur.reviewed_at = timezone.now()
        cur.review_comment = request.data.get("admin_note", "")
        cur.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment"])

        # For delete requests, archive the course on approval.
        if cur.request_type == "delete":
            cur.course.status = "archived"
            cur.course.save(update_fields=["status", "updated_at"])

        # Notify the requesting trainer.
        try:
            from apps.notifications.models import notify_user

            action_word = "deleted" if cur.request_type == "delete" else "may now edit"
            notify_user(
                cur.trainer,
                f"Course {cur.request_type} approved: {cur.course.title}",
                f"Your request to {cur.request_type} '{cur.course.title}' was approved. "
                f"The course {action_word}.",
                "success",
                f"/training/{cur.course_id}",
            )
        except Exception:
            pass
        return Response(
            {"message": "Request approved.", "data": CourseModificationRequestSerializer(cur).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="decline")
    def decline(self, request, pk=None):
        """Admin declines a course update/delete request."""
        cur = self.get_object()
        user = request.user
        user_role_name = user.role.name if user.role_id else None
        if user_role_name != "cj_admin" and not user.is_superuser:
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can decline."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if cur.status != "pending":
            return Response(
                {
                    "error": {
                        "code": "invalid_state",
                        "message": f"Request is already {cur.status}.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone

        cur.status = "rejected"
        cur.reviewed_by = user
        cur.reviewed_at = timezone.now()
        cur.review_comment = request.data.get("admin_note", "")
        cur.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment"])
        try:
            from apps.notifications.models import notify_user

            notify_user(
                cur.trainer,
                f"Course {cur.request_type} request declined: {cur.course.title}",
                f"Your request to {cur.request_type} '{cur.course.title}' was declined. "
                f"{cur.review_comment}",
                "warning",
                f"/training/{cur.course_id}",
            )
        except Exception:
            pass
        return Response(
            {"message": "Request declined.", "data": CourseModificationRequestSerializer(cur).data},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Live Session Request (Report 3 §7.5/OS.4) — candidate schedule requests
# ---------------------------------------------------------------------------


class LiveSessionRequestViewSet(ModelViewSet):
    """Candidate requests for the trainer to schedule a live session, plus
    trainer scheduling against a request.

    Candidates create requests; trainers list their course's requests and
    schedule a session (which notifies the candidate).
    """

    queryset = LiveSessionRequest.objects.select_related("course", "student")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = LiveSessionRequestSerializer
    http_method_names = ["get", "head", "options", "post"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        user_role_name = user.role.name if user.role_id else None
        if user_role_name in ("cj_admin", "trainer") or user.is_superuser:
            # Trainers see requests for their own courses
            if user_role_name == "trainer":
                return qs.filter(course__created_by=user)
            return qs
        # Candidates see their own requests
        return qs.filter(student=user)

    def list(self, request, *args, **kwargs):
        # Serialize directly (NOT super().list()) so pagination cannot wrap
        # the payload into {count, results} — the frontend expects an array.
        qs = self.filter_queryset(self.get_queryset())
        return Response(
            {"message": "OK", "data": self.get_serializer(qs, many=True).data},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        course_id = request.data.get("course")
        if not course_id:
            return Response(
                {"error": {"code": "validation_error", "message": "course is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        lsr = LiveSessionRequest.objects.create(
            course_id=course_id,
            student=request.user,
            preferred_times=request.data.get("preferred_times", []),
            note=request.data.get("note", ""),
        )
        # Notify the trainer.
        try:
            from apps.notifications.models import notify_user

            course = lsr.course
            if course.created_by:
                notify_user(
                    course.created_by,
                    f"Live-session request: {course.title}",
                    f"{request.user.full_name or request.user.email} requested a live session. "
                    f"Note: {lsr.note}",
                    "session",
                    f"/training/{course.id}",
                )
        except Exception:
            pass
        return Response(
            {"message": "Request sent to trainer.", "data": LiveSessionRequestSerializer(lsr).data},
            status=status.HTTP_201_CREATED,
        )
