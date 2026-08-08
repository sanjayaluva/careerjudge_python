"""Serializers for the Counseling module."""

from rest_framework import serializers

from .models import (
    CounselingCategory,
    CounselingSession,
    CounselingSettings,
    CounsellorProfile,
    FollowupSession,
    SessionCancellation,
    SessionFeedback,
    SessionSummary,
    TimeSlot,
)


class CounselingCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CounselingCategory
        fields = ["id", "name", "description", "is_active"]
        read_only_fields = ["id"]


class CounsellorProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    bio = serializers.CharField(source="user.profile.bio", read_only=True, default="")
    hourly_rate = serializers.DecimalField(
        source="user.profile.hourly_rate",
        max_digits=10,
        decimal_places=2,
        read_only=True,
        default=50,
    )
    meeting_url = serializers.CharField(
        source="user.profile.meeting_url", read_only=True, default=""
    )
    is_available = serializers.BooleanField(
        source="user.profile.is_available_for_counseling", read_only=True, default=True
    )
    cancellation_count = serializers.IntegerField(
        source="user.profile.cancellation_count", read_only=True, default=0
    )
    # Doc 3 fields (read from UserProfile)
    gender = serializers.CharField(source="user.profile.gender", read_only=True, default="")
    avatar = serializers.SerializerMethodField()
    language_of_communication = serializers.CharField(
        source="user.profile.language_of_communication", read_only=True, default=""
    )
    geographical_location = serializers.CharField(
        source="user.profile.geographical_location", read_only=True, default=""
    )
    category_names = serializers.SerializerMethodField()
    upcoming_slot_count = serializers.SerializerMethodField()

    class Meta:
        model = CounsellorProfile
        fields = [
            "id",
            "user",
            "user_email",
            "full_name",
            "bio",
            "hourly_rate",
            "meeting_url",
            "categories",
            "category_names",
            "is_available",
            "cancellation_count",
            "gender",
            "avatar",
            "language_of_communication",
            "geographical_location",
            "upcoming_slot_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_email",
            "full_name",
            "bio",
            "hourly_rate",
            "meeting_url",
            "is_available",
            "cancellation_count",
            "gender",
            "avatar",
            "language_of_communication",
            "geographical_location",
            "upcoming_slot_count",
            "category_names",
            "created_at",
            "updated_at",
        ]

    def get_category_names(self, obj):
        return [c.get_name_display() for c in obj.categories.all()]

    def get_avatar(self, obj):
        """Return avatar URL or empty string if no avatar."""
        try:
            if obj.user.profile.avatar:
                return obj.user.profile.avatar.url
        except (AttributeError, ValueError):
            pass
        return ""

    def get_upcoming_slot_count(self, obj):
        from django.utils import timezone

        return obj.timeslots.filter(status="available", start_time__gte=timezone.now()).count()


class TimeSlotSerializer(serializers.ModelSerializer):
    counsellor_name = serializers.CharField(source="counsellor.full_name", read_only=True)

    class Meta:
        model = TimeSlot
        fields = [
            "id",
            "counsellor",
            "counsellor_name",
            "start_time",
            "end_time",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "counsellor_name", "created_at"]


class CounselingSessionSerializer(serializers.ModelSerializer):
    counselee_name = serializers.CharField(
        source="counselee.full_name", read_only=True, default=None
    )
    counselee_email = serializers.CharField(source="counselee.email", read_only=True)
    counsellor_name = serializers.CharField(source="counsellor.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    timeslot_detail = TimeSlotSerializer(source="timeslot", read_only=True)

    class Meta:
        model = CounselingSession
        fields = [
            "id",
            "counselee",
            "counselee_name",
            "counselee_email",
            "counsellor",
            "counsellor_name",
            "category",
            "category_name",
            "timeslot",
            "timeslot_detail",
            "topic",
            "description",
            "terms_accepted",
            "status",
            "payment_status",
            "mode",
            "fee",
            "booked_at",
            "confirmed_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "counselee",
            "counselee_name",
            "counselee_email",
            "counsellor_name",
            "category_name",
            "timeslot_detail",
            "status",
            "payment_status",
            "fee",
            "booked_at",
            "confirmed_at",
            "completed_at",
        ]


class SessionCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionCancellation
        fields = [
            "id",
            "session",
            "cancelled_by",
            "reason",
            "refund_tier",
            "refund_amount",
            "cancelled_at",
        ]
        read_only_fields = ["id", "refund_tier", "refund_amount", "cancelled_at"]


class SessionSummarySerializer(serializers.ModelSerializer):
    """Serializer for counsellor's post-session summary (Doc 3)."""

    class Meta:
        model = SessionSummary
        fields = [
            "id",
            "session",
            "counsellor",
            "client_details",
            "summary",
            "provisional_diagnosis",
            "case_prognosis",
            "session_smoothness",
            "smoothness_reason",
            "followup_recommended",
            "recommendations",
            "created_at",
        ]
        read_only_fields = ["id", "counsellor", "created_at"]


class SessionFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for counselee's post-session feedback (Doc 3).

    Per Doc 3 feedback form (8 questions).
    """

    class Meta:
        model = SessionFeedback
        fields = [
            "id",
            "session",
            "counselee",
            # Doc 3 feedback form fields
            "session_usefulness",
            "usefulness_text",
            "counsellor_empathy",
            "session_ending",
            "would_rechoose",
            "rechoose_text",
            "improvement_suggestions",
            "counsellor_rating",
            # Legacy fields (backward compatibility)
            "rating",
            "experience_text",
            "counsellor_effectiveness",
            "created_at",
        ]
        read_only_fields = ["id", "counselee", "created_at"]


class FollowupSessionSerializer(serializers.ModelSerializer):
    counsellor_name = serializers.CharField(source="counsellor.full_name", read_only=True)
    counselee_name = serializers.CharField(
        source="original_session.counselee.full_name", read_only=True, default=None
    )

    class Meta:
        model = FollowupSession
        fields = [
            "id",
            "original_session",
            "counsellor",
            "counsellor_name",
            "counselee_name",
            "proposed_time",
            "status",
            "confirmed_session",
            "created_at",
        ]
        read_only_fields = ["id", "counsellor_name", "counselee_name", "created_at"]


class CounselingSettingsSerializer(serializers.ModelSerializer):
    """Serializer for counseling settings (terms, cancellation policy)."""

    class Meta:
        model = CounselingSettings
        fields = ["id", "terms_and_conditions", "cancellation_policy", "updated_at"]
        read_only_fields = ["id", "updated_at"]
