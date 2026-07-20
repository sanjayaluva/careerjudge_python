"""Serializers for the Training module."""

from rest_framework import serializers

from apps.assessment.serializers import AssessmentListSerializer

from .models import (
    Assignment,
    CourseAssessment,
    CourseCompletionParameter,
    CourseLesson,
    CourseProgress,
    CourseRegistration,
    LessonTopic,
    LiveSession,
    SessionContent,
    TopicSession,
    TrainingCategory,
    TrainingCourse,
)


class TrainingCategorySerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(source="courses.count", read_only=True)

    class Meta:
        model = TrainingCategory
        fields = ["id", "name", "description", "is_active", "course_count", "created_at"]
        read_only_fields = ["id", "created_at", "course_count"]


class SessionContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionContent
        fields = [
            "id",
            "session",
            "title",
            "content_format",
            "content_url",
            "text_content",
            "duration_seconds",
            "order",
        ]
        read_only_fields = ["id"]


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "id",
            "session",
            "title",
            "description",
            "resource_url",
            "report_submission_enabled",
            "report_instructions",
            "order",
        ]
        read_only_fields = ["id"]


class TopicSessionSerializer(serializers.ModelSerializer):
    contents = SessionContentSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = TopicSession
        fields = ["id", "topic", "title", "description", "order", "contents", "assignments"]
        read_only_fields = ["id", "contents", "assignments"]


class LessonTopicSerializer(serializers.ModelSerializer):
    sessions = TopicSessionSerializer(many=True, read_only=True)

    class Meta:
        model = LessonTopic
        fields = ["id", "lesson", "title", "description", "order", "sessions"]
        read_only_fields = ["id", "sessions"]


class CourseLessonSerializer(serializers.ModelSerializer):
    topics = LessonTopicSerializer(many=True, read_only=True)

    class Meta:
        model = CourseLesson
        fields = ["id", "course", "title", "description", "order", "week_number", "topics"]
        read_only_fields = ["id", "topics", "course"]


class CourseAssessmentSerializer(serializers.ModelSerializer):
    assessment_detail = AssessmentListSerializer(source="assessment", read_only=True)

    class Meta:
        model = CourseAssessment
        fields = [
            "id",
            "course",
            "assessment",
            "assessment_detail",
            "level",
            "session",
            "title",
            "is_scored",
            "order",
        ]
        read_only_fields = ["id", "assessment_detail", "course"]


class LiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = [
            "id",
            "course",
            "title",
            "description",
            "mode",
            "meeting_url",
            "venue",
            "scheduled_at",
            "duration_minutes",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "course"]


class CourseCompletionParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCompletionParameter
        fields = ["id", "course", "content_type", "content_id", "is_mandatory"]
        read_only_fields = ["id"]


class CourseProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseProgress
        fields = [
            "id",
            "registration",
            "content_type",
            "content_id",
            "is_completed",
            "time_spent_seconds",
            "last_accessed_at",
        ]
        read_only_fields = ["id"]


class CourseRegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True, default=None)
    student_email = serializers.CharField(source="student.email", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = CourseRegistration
        fields = [
            "id",
            "course",
            "course_title",
            "student",
            "student_name",
            "student_email",
            "payment_status",
            "completion_status",
            "started_at",
            "completed_at",
            "registered_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "student_name",
            "student_email",
            "course_title",
            "started_at",
            "completed_at",
            "registered_at",
        ]


class TrainingCourseListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    registration_count = serializers.IntegerField(source="registrations.count", read_only=True)

    class Meta:
        model = TrainingCourse
        fields = [
            "id",
            "title",
            "objective",
            "image",
            "category",
            "category_name",
            "course_type",
            "schedule_type",
            "duration_days",
            "price",
            "status",
            "created_by",
            "created_by_name",
            "registration_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "registration_count"]


class TrainingCourseSerializer(serializers.ModelSerializer):
    """Full serializer with nested children for detail views."""

    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    lessons = CourseLessonSerializer(many=True, read_only=True)
    live_sessions = LiveSessionSerializer(many=True, read_only=True)
    assessments = CourseAssessmentSerializer(many=True, read_only=True)
    registration_count = serializers.IntegerField(source="registrations.count", read_only=True)

    class Meta:
        model = TrainingCourse
        fields = [
            "id",
            "title",
            "objective",
            "description",
            "image",
            "category",
            "category_name",
            "course_type",
            "schedule_type",
            "duration_days",
            "price",
            "status",
            "created_by",
            "created_by_name",
            "registration_count",
            "lessons",
            "live_sessions",
            "assessments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "lessons",
            "live_sessions",
            "assessments",
            "registration_count",
        ]
