"""Serializers for the Assessment module."""

from rest_framework import serializers

from apps.question_bank.serializers import QuestionListSerializer

from .models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
    QuestionAttempt,
    SectionScore,
)


class AssessmentSectionSerializer(serializers.ModelSerializer):
    subsections = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentSection
        fields = [
            "id",
            "assessment",
            "parent",
            "title",
            "description",
            "level",
            "order",
            "duration_seconds",
            "subsections",
        ]
        read_only_fields = ["id"]

    def get_subsections(self, obj):
        children = obj.subsections.all().order_by("order")
        return AssessmentSectionSerializer(children, many=True).data


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    question_detail = QuestionListSerializer(source="question", read_only=True)

    class Meta:
        model = AssessmentQuestion
        fields = [
            "id",
            "section",
            "question",
            "order",
            "sub_question_index",
            "score_override",
            "duration_seconds",
            "question_detail",
        ]
        read_only_fields = ["id", "question_detail"]


class AssessmentSerializer(serializers.ModelSerializer):
    sections = AssessmentSectionSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "objective",
            "description",
            "instructions",
            "status",
            "total_duration_seconds",
            "timer_level",
            "display_order",
            "navigation_rule",
            "attempt_rule",
            "created_by",
            "created_at",
            "updated_at",
            "sections",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "sections"]


class AssessmentListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    section_count = serializers.IntegerField(source="sections.count", read_only=True)
    session_count = serializers.IntegerField(source="sessions.count", read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "objective",
            "status",
            "total_duration_seconds",
            "display_order",
            "navigation_rule",
            "attempt_rule",
            "created_by",
            "created_by_name",
            "section_count",
            "session_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class AssessmentSessionSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(source="assessment.title", read_only=True)
    candidate_name = serializers.CharField(
        source="candidate.full_name", read_only=True, default=None
    )

    class Meta:
        model = AssessmentSession
        fields = [
            "id",
            "assessment",
            "assessment_title",
            "candidate",
            "candidate_name",
            "status",
            "started_at",
            "suspended_at",
            "resumed_at",
            "completed_at",
            "total_score",
            "max_score",
            "percentage",
        ]
        read_only_fields = [
            "id",
            "candidate",
            "started_at",
            "suspended_at",
            "resumed_at",
            "completed_at",
            "total_score",
            "max_score",
            "percentage",
            "assessment_title",
            "candidate_name",
        ]


class QuestionAttemptSerializer(serializers.ModelSerializer):
    question_detail = QuestionListSerializer(source="question", read_only=True)

    class Meta:
        model = QuestionAttempt
        fields = [
            "id",
            "session",
            "question",
            "section",
            "sub_question_index",
            "status",
            "raw_answer",
            "score",
            "max_score",
            "answered_at",
            "time_spent_seconds",
            "question_detail",
        ]
        read_only_fields = ["id", "score", "max_score", "answered_at", "question_detail"]


class SectionScoreSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = SectionScore
        fields = [
            "id",
            "session",
            "section",
            "section_title",
            "raw_score",
            "max_score",
            "percentage",
        ]
        read_only_fields = ["id", "raw_score", "max_score", "percentage", "section_title"]
