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
    CourseLesson,
    CourseMessage,
    CourseProgress,
    CourseRegistration,
    LessonTopic,
    LiveSession,
    LiveSessionConsent,
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
    CourseProgressSerializer,
    CourseRegistrationSerializer,
    InteractiveQuestionSerializer,
    LessonTopicSerializer,
    LiveSessionConsentSerializer,
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
        "register": "add",  # student self-registers
        "registrations": "view",
        "progress": "change",
        "my_courses": "view",
        "progress_summary": "view",
        "messages": "add",  # student + trainer can send messages
        "assignment_reports": "add",  # student submits
        "review_report": "change",  # trainer reviews
        "consent": "add",  # student consents to live session
        "consents": "view",  # trainer views consent list
        "interactive_questions": "change",  # trainer adds questions to content
        "notify_students": "change",  # trainer triggers notification manually
    }


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
        serializer.save(course=course)
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

    @action(detail=True, methods=["post"])
    def register(self, request, pk=None):
        """Student registers for a course (SRS §6).

        Creates a CourseRegistration with payment_status='pending' (the
        payment gateway integration is a separate step). For scheduled
        courses, started_at is set immediately per SRS §6 rule: 'If
        training course is scheduled, course duration starts from this
        time'. For non-scheduled, started_at stays null until the
        student first accesses course content.
        """
        from django.utils import timezone

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
        reg, created = CourseRegistration.objects.get_or_create(
            course=course,
            student=request.user,
            defaults={
                "payment_status": "pending",
                "completion_status": "not_started",
                "started_at": timezone.now() if course.schedule_type == "scheduled" else None,
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
        return Response(
            {"message": "Registration created.", "data": CourseRegistrationSerializer(reg).data},
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

        return Response(
            {
                "message": "OK",
                "data": {
                    "completion_percentage": completion_pct,
                    "completed_count": len(completed),
                    "total_count": len(progress_records),
                    "total_time_spent_seconds": total_time_spent,
                    "total_time_allowed_seconds": total_time_allowed,
                    "time_left_seconds": time_left,
                    "is_expired": is_expired,
                    "last_accessed_at": last_accessed.isoformat() if last_accessed else None,
                    "last_content": last_content,
                    "completion_status": reg.completion_status,
                    "started_at": reg.started_at.isoformat() if reg.started_at else None,
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
        report, created = AssignmentReport.objects.update_or_create(
            assignment=assignment,
            student=request.user,
            defaults={
                "report_text": request.data.get("report_text", ""),
                "report_file_url": request.data.get("report_file_url", ""),
                "status": "submitted",
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
        from django.utils import timezone

        report.trainer_score = request.data.get("trainer_score")
        report.trainer_feedback = request.data.get("trainer_feedback", "")
        report.reviewed_by = user
        report.reviewed_at = timezone.now()
        report.status = "reviewed"
        report.save()
        return Response(
            {"message": "Report reviewed.", "data": AssignmentReportSerializer(report).data},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Nested resource ViewSets (lessons/topics/sessions/contents/assignments)
# ---------------------------------------------------------------------------


class CourseLessonViewSet(ModelViewSet):
    """CRUD for lessons within a course."""

    queryset = CourseLesson.objects.select_related("course")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = CourseLessonSerializer

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
        serializer = LessonTopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lesson=lesson)
        return Response(
            {"message": "Topic created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class LessonTopicViewSet(ModelViewSet):
    """CRUD for topics within a lesson."""

    queryset = LessonTopic.objects.select_related("lesson")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = LessonTopicSerializer

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
        serializer = TopicSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(topic=topic)
        return Response(
            {"message": "Session created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class TopicSessionViewSet(ModelViewSet):
    """CRUD for sessions within a topic."""

    queryset = TopicSession.objects.select_related("topic")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = TopicSessionSerializer

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
        serializer = SessionContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session)
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
        serializer = AssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session)
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
        body: {"status": "consented" | "declined"}

        Creates a LiveSessionConsent record. A notification is sent to the
        trainer via the post_save signal (apps/training/signals.py).
        """
        live_session = self.get_object()
        status_val = request.data.get("status", "consented")
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


# ---------------------------------------------------------------------------
# Session Content → Interactive Questions (SRS §2.3.1 Timeliner)
# ---------------------------------------------------------------------------


class SessionContentViewSet(ModelViewSet):
    """CRUD for session content + interactive questions (Timeliner)."""

    queryset = SessionContent.objects.select_related("session")
    permission_classes = [IsAuthenticated, HasTrainingPermission]
    serializer_class = SessionContentSerializer

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
