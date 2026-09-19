"""Serializers for the Training module."""

from rest_framework import serializers

from apps.assessment.serializers import AssessmentListSerializer

from .models import (
    Assignment,
    AssignmentReport,
    CourseAssessment,
    CourseCompletionParameter,
    CourseLesson,
    CourseMessage,
    CourseModificationRequest,
    CourseProgress,
    CourseRegistration,
    InteractiveQuestion,
    LessonTopic,
    LiveSession,
    LiveSessionConsent,
    LiveSessionRequest,
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


class InteractiveQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractiveQuestion
        fields = [
            "id",
            "session_content",
            "question_text",
            "trigger_timestamp",
            "options",
            "correct_jump_to",
            "incorrect_jump_to",
            "order",
        ]
        read_only_fields = ["id", "session_content"]


class SessionContentSerializer(serializers.ModelSerializer):
    interactive_questions = InteractiveQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = SessionContent
        fields = [
            "id",
            "session",
            "title",
            "content_format",
            "content_url",
            "document",
            "media_file",
            "text_content",
            "duration_seconds",
            "order",
            "sequence_order",
            "interactive_questions",
        ]
        read_only_fields = ["id", "interactive_questions", "session"]


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
            "is_mandatory",
            "submission_deadline",
            "report_instructions",
            "order",
        ]
        read_only_fields = ["id", "session"]


class TopicSessionSerializer(serializers.ModelSerializer):
    contents = SessionContentSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = TopicSession
        fields = ["id", "topic", "title", "description", "order", "contents", "assignments"]
        read_only_fields = ["id", "contents", "assignments", "topic"]


class LessonTopicSerializer(serializers.ModelSerializer):
    sessions = TopicSessionSerializer(many=True, read_only=True)

    class Meta:
        model = LessonTopic
        fields = ["id", "lesson", "title", "description", "order", "sessions"]
        read_only_fields = ["id", "sessions", "lesson"]


class CourseLessonSerializer(serializers.ModelSerializer):
    topics = LessonTopicSerializer(many=True, read_only=True)

    class Meta:
        model = CourseLesson
        fields = ["id", "course", "title", "description", "order", "week_number", "topics"]
        read_only_fields = ["id", "topics", "course"]


class CourseAssessmentSerializer(serializers.ModelSerializer):
    assessment_detail = AssessmentListSerializer(source="assessment", read_only=True)
    session_title = serializers.CharField(source="session.title", read_only=True, default=None)
    topic_title = serializers.CharField(source="topic.title", read_only=True, default=None)
    lesson_title = serializers.CharField(source="lesson.title", read_only=True, default=None)

    class Meta:
        model = CourseAssessment
        fields = [
            "id",
            "course",
            "assessment",
            "assessment_detail",
            "level",
            "session",
            "session_title",
            "topic",
            "topic_title",
            "lesson",
            "lesson_title",
            "title",
            "is_scored",
            "order",
        ]
        read_only_fields = [
            "id",
            "assessment_detail",
            "course",
            "session_title",
            "topic_title",
            "lesson_title",
        ]

    def validate(self, attrs):
        """Report 4 Trainer-9: the target must match the level."""
        level = attrs.get("level", getattr(self.instance, "level", "end_of_session"))
        if level in ("during_session", "end_of_session") and not attrs.get("session"):
            raise serializers.ValidationError(
                {"session": "Pick the session this assessment attaches to."}
            )
        if level == "end_of_topic" and not attrs.get("topic"):
            raise serializers.ValidationError(
                {"topic": "Pick the topic this assessment attaches to."}
            )
        if level == "end_of_lesson" and not attrs.get("lesson"):
            raise serializers.ValidationError(
                {"lesson": "Pick the lesson this assessment attaches to."}
            )
        return attrs


class LiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = [
            "id",
            "course",
            "title",
            "description",
            "mode",
            "schedule_mode",
            "depends_on",
            "meeting_url",
            "venue",
            "scheduled_at",
            "duration_minutes",
            "status",
            "rescheduled_from",
            "reschedule_reason",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "course", "rescheduled_from"]


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
            "registration_form",
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
            "content_sequencing_enabled",
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
            "content_sequencing_enabled",
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


class AssignmentReportFileSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import AssignmentReportFile

        model = AssignmentReportFile
        fields = ["id", "file", "file_type", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class AssignmentReportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True, default=None)
    student_email = serializers.CharField(source="student.email", read_only=True)
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, default=None
    )
    files = AssignmentReportFileSerializer(many=True, read_only=True)

    class Meta:
        model = AssignmentReport
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "student",
            "student_name",
            "student_email",
            "report_text",
            "report_file_url",
            "report_file",
            "files",
            "late_submission_approved",
            "status",
            "trainer_score",
            "trainer_feedback",
            "reviewed_at",
            "reviewed_by",
            "reviewed_by_name",
            "submitted_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "student_name",
            "student_email",
            "assignment_title",
            "status",
            "reviewed_at",
            "reviewed_by",
            "reviewed_by_name",
            "submitted_at",
            "updated_at",
        ]


class CourseMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True, default=None)
    sender_email = serializers.CharField(source="sender.email", read_only=True)
    course_title = serializers.CharField(source="registration.course.title", read_only=True)

    class Meta:
        model = CourseMessage
        fields = [
            "id",
            "registration",
            "course_title",
            "sender",
            "sender_name",
            "sender_email",
            "body",
            "is_read",
            "sent_at",
        ]
        read_only_fields = [
            "id",
            "sender",
            "sender_name",
            "sender_email",
            "course_title",
            "sent_at",
        ]


class LiveSessionConsentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True, default=None)
    student_email = serializers.CharField(source="student.email", read_only=True)
    live_session_title = serializers.CharField(source="live_session.title", read_only=True)

    class Meta:
        model = LiveSessionConsent
        fields = [
            "id",
            "live_session",
            "live_session_title",
            "student",
            "student_name",
            "student_email",
            "status",
            "consented_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "student_name",
            "student_email",
            "live_session_title",
            "consented_at",
        ]


class CourseModificationRequestSerializer(serializers.ModelSerializer):
    """Report 3 §7.1/§7.2: trainer request to update/delete a published course."""

    course_title = serializers.CharField(source="course.title", read_only=True)
    trainer_name = serializers.CharField(source="trainer.full_name", read_only=True, default=None)
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = CourseModificationRequest
        fields = [
            "id",
            "course",
            "course_title",
            "trainer",
            "trainer_name",
            "request_type",
            "reason",
            "status",
            "review_comment",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "trainer",
            "trainer_name",
            "status",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "course_title",
        ]


class LiveSessionRequestSerializer(serializers.ModelSerializer):
    """Report 3 §7.5/OS.4: candidate request to schedule a live session."""

    course_title = serializers.CharField(source="course.title", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True, default=None)

    class Meta:
        model = LiveSessionRequest
        fields = [
            "id",
            "course",
            "course_title",
            "student",
            "student_name",
            "preferred_times",
            "note",
            "status",
            "scheduled_session",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "student_name",
            "status",
            "scheduled_session",
            "created_at",
            "course_title",
        ]
