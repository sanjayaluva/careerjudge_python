"""Serializers for the Assessment module."""

from rest_framework import serializers

from apps.question_bank.serializers import QuestionDetailSerializer, QuestionListSerializer

from .models import (
    Assessment,
    AssessmentModificationRequest,
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
            "order_mode",
            "duration_seconds",
            "delivery_count",
            "subsections",
        ]
        read_only_fields = ["id", "assessment"]

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
        read_only_fields = ["id", "section", "question_detail"]


class AssessmentSerializer(serializers.ModelSerializer):
    sections = AssessmentSectionSerializer(many=True, read_only=True)
    assessment_type_label = serializers.CharField(
        source="get_assessment_type_display", read_only=True
    )
    section_count = serializers.IntegerField(source="sections.count", read_only=True)
    session_count = serializers.IntegerField(source="sessions.count", read_only=True)

    def get_question_count(self, obj):
        """Count total questions assigned across ALL sections (including
        nested subsections). Uses a single query for efficiency."""
        from apps.assessment.models import AssessmentQuestion

        section_ids = obj.sections.values_list("id", flat=True)
        return AssessmentQuestion.objects.filter(section_id__in=section_ids).count()

    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "objective",
            "description",
            "instructions",
            "status",
            "assessment_type",
            "assessment_type_label",
            "total_duration_seconds",
            "timer_level",
            "display_order",
            "navigation_rule",
            "attempt_rule",
            "price",
            "created_by",
            "created_at",
            "updated_at",
            "section_count",
            "question_count",
            "session_count",
            "sections",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "section_count",
            "question_count",
            "session_count",
            "sections",
        ]


class AssessmentListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    section_count = serializers.IntegerField(source="sections.count", read_only=True)
    session_count = serializers.IntegerField(source="sessions.count", read_only=True)
    assessment_type_label = serializers.CharField(
        source="get_assessment_type_display", read_only=True
    )

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "objective",
            "status",
            "assessment_type",
            "assessment_type_label",
            "total_duration_seconds",
            "display_order",
            "navigation_rule",
            "attempt_rule",
            "price",
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
    # Expose assessment-level config the candidate player needs at runtime
    total_duration_seconds = serializers.IntegerField(
        source="assessment.total_duration_seconds", read_only=True
    )
    navigation_rule = serializers.CharField(source="assessment.navigation_rule", read_only=True)
    display_order = serializers.CharField(source="assessment.display_order", read_only=True)
    timer_level = serializers.CharField(source="assessment.timer_level", read_only=True)
    # Effective time budget: assessment-level timer, or the sum of the
    # per-level (section/question) timers when the timer is set lower down.
    aggregate_duration_seconds = serializers.IntegerField(
        source="assessment.aggregate_duration_seconds", read_only=True
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
            "total_duration_seconds",
            "aggregate_duration_seconds",
            "navigation_rule",
            "display_order",
            "timer_level",
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
            "total_duration_seconds",
            "aggregate_duration_seconds",
        ]


class QuestionAttemptSerializer(serializers.ModelSerializer):
    """Serializer for a candidate's attempt at one question.

    Uses ``QuestionDetailSerializer`` for ``question_detail`` because the
    session player needs the full question including options, flash items,
    hotspot areas, passage, image, etc. to render the answer input.
    """

    question_detail = QuestionDetailSerializer(source="question", read_only=True)
    # Per-level timer metadata for the player (populated when the view passes
    # the timer context; None otherwise, e.g. the single-attempt answer echo).
    # ``timer_section_id`` is the ancestor section that governs this
    # question's section-level timer; ``section_duration_seconds`` is that
    # section's duration. ``question_duration_seconds`` is this question's own
    # per-question timer (used when timer_level='question').
    section_duration_seconds = serializers.SerializerMethodField()
    timer_section_id = serializers.SerializerMethodField()
    question_duration_seconds = serializers.SerializerMethodField()
    # ASM-5 (§5.1): the section's per-level delivery order mode, so the player
    # can randomise questions within RANDOM sections.
    section_order_mode = serializers.SerializerMethodField()

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
            "section_duration_seconds",
            "timer_section_id",
            "question_duration_seconds",
            "section_order_mode",
            "question_detail",
        ]
        read_only_fields = ["id", "score", "max_score", "answered_at", "question_detail"]

    def _timer_section(self, obj):
        section_map = self.context.get("section_timer_map") or {}
        return section_map.get(obj.section_id, (None, None))

    def get_section_order_mode(self, obj):
        return obj.section.order_mode if obj.section_id else "STATIC"

    def get_timer_section_id(self, obj):
        return self._timer_section(obj)[0]

    def get_section_duration_seconds(self, obj):
        return self._timer_section(obj)[1]

    def get_question_duration_seconds(self, obj):
        durations = self.context.get("aq_durations") or {}
        return durations.get((obj.section_id, obj.question_id, obj.sub_question_index))


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


class AssessmentModificationRequestSerializer(serializers.ModelSerializer):
    """SRS §2.2/§2.3: non-admin request to edit the title of / delete a
    published assessment."""

    assessment_title = serializers.CharField(source="assessment.title", read_only=True)
    requester_name = serializers.CharField(
        source="requester.full_name", read_only=True, default=None
    )
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = AssessmentModificationRequest
        fields = [
            "id",
            "assessment",
            "assessment_title",
            "requester",
            "requester_name",
            "action",
            "proposed_title",
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
            "assessment_title",
            "requester",
            "requester_name",
            "action",
            "proposed_title",
            "status",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
        ]
