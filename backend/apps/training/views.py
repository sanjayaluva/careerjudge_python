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
    CourseLesson,
    CourseProgress,
    CourseRegistration,
    LessonTopic,
    TopicSession,
    TrainingCategory,
    TrainingCourse,
)
from .serializers import (
    AssignmentSerializer,
    CourseAssessmentSerializer,
    CourseLessonSerializer,
    CourseProgressSerializer,
    CourseRegistrationSerializer,
    LessonTopicSerializer,
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
        """List or add lessons to a course (SRS §2.2)."""
        course = self.get_object()
        if request.method == "GET":
            lessons = course.lessons.all()
            return Response(
                {"message": "OK", "data": CourseLessonSerializer(lessons, many=True).data},
                status=status.HTTP_200_OK,
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
