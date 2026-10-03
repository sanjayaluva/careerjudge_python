"""Serializers for the Counseling module."""

import re

from django.utils.text import slugify
from rest_framework import serializers

from .models import (
    CounselingCategory,
    CounselingSession,
    CounsellorProfile,
    FollowupSession,
    SessionCancellation,
    SessionFeedback,
    SessionSummary,
    TimeSlot,
)

# Lowercase letters/digits/underscores, not digits only (set-categories reads
# an all-digit value as a category id).
_CODE_RE = re.compile(r"^(?!\d+$)[a-z0-9_]+$")


class CounselingCategorySerializer(serializers.ModelSerializer):
    """Report 9 #105: CJ Admin adds / renames / (de)activates categories.

    ``name`` is the stable code: optional on create (made from the label) and
    fixed afterwards, so existing tags, filters and links keep working.
    ``counsellor_count`` / ``session_count`` tell the admin screen whether a
    category is in use (in use → deactivate rather than delete)."""

    name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    label = serializers.CharField(max_length=100, required=False)
    counsellor_count = serializers.IntegerField(read_only=True, default=0)
    session_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = CounselingCategory
        fields = [
            "id",
            "name",
            "label",
            "description",
            "is_active",
            "counsellor_count",
            "session_count",
        ]
        read_only_fields = ["id"]

    def validate_label(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter the category name.")
        clash = CounselingCategory.objects.filter(label__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value

    def validate_name(self, value):
        value = (value or "").strip().lower()
        if self.instance is not None:
            if value and value != self.instance.name:
                raise serializers.ValidationError("The category code cannot be changed.")
            return self.instance.name
        if value and not _CODE_RE.match(value):
            raise serializers.ValidationError(
                "Use lowercase letters, digits and underscores (not digits only) for the code."
            )
        if value and CounselingCategory.objects.filter(name=value).exists():
            raise serializers.ValidationError("A category with this code already exists.")
        return value

    def validate(self, attrs):
        if self.instance is None:
            label = attrs.get("label") or ""
            if not label:
                # Older clients sent only the code; use it as the label.
                label = (attrs.get("name") or "").strip()
                if not label:
                    raise serializers.ValidationError({"label": "Enter the category name."})
                attrs["label"] = self.validate_label(label)
            if not attrs.get("name"):
                attrs["name"] = _unique_code(attrs["label"])
        return attrs


def _unique_code(label: str) -> str:
    base = (slugify(label).replace("-", "_") or "category")[:40]
    if base.isdigit():
        base = f"category_{base}"
    code, n = base, 2
    while CounselingCategory.objects.filter(name=code).exists():
        code, n = f"{base}_{n}", n + 1
    return code


def category_label(category) -> str | None:
    return (category.label or category.name) if category is not None else None


class CounsellorProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    bio = serializers.CharField(source="user.profile.bio", read_only=True, default="")
    # Report 3 §1.7: expose gender / avatar / language / location so the
    # browse view shows them to candidates.
    gender = serializers.CharField(source="user.profile.gender", read_only=True, default="")
    avatar = serializers.ImageField(source="user.profile.avatar", read_only=True, default=None)
    language = serializers.CharField(
        source="user.profile.language_of_communication", read_only=True, default=""
    )
    location = serializers.CharField(source="user.profile.location", read_only=True, default="")
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
    category_names = serializers.SerializerMethodField()
    upcoming_slot_count = serializers.SerializerMethodField()
    # Report 8 #42/#43: details counselees need to choose a counsellor.
    age = serializers.IntegerField(source="user.profile.age", read_only=True, default=None)
    languages = serializers.JSONField(
        source="user.profile.communicative_languages", read_only=True, default=list
    )
    region = serializers.CharField(source="user.profile.city", read_only=True, default="")
    professional_qualification = serializers.CharField(
        source="user.profile.highest_education", read_only=True, default=""
    )
    current_position = serializers.CharField(
        source="user.profile.current_position", read_only=True, default=""
    )
    work_experience = serializers.CharField(
        source="user.profile.work_experience", read_only=True, default=""
    )

    class Meta:
        model = CounsellorProfile
        fields = [
            "age",
            "languages",
            "region",
            "professional_qualification",
            "current_position",
            "work_experience",
            "id",
            "user",
            "user_email",
            "full_name",
            "bio",
            "gender",
            "avatar",
            "language",
            "location",
            "hourly_rate",
            "meeting_url",
            "categories",
            "category_names",
            "is_available",
            "cancellation_count",
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
            "gender",
            "avatar",
            "language",
            "location",
            "hourly_rate",
            "meeting_url",
            "is_available",
            "cancellation_count",
            "upcoming_slot_count",
            "category_names",
            "created_at",
            "updated_at",
        ]

    def get_category_names(self, obj):
        # Report 9 #105: the admin-managed label (inactive ones included —
        # they stay on the counsellors already tagged with them).
        return [category_label(c) for c in obj.categories.all()]

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
    category_name = serializers.SerializerMethodField()
    timeslot_detail = TimeSlotSerializer(source="timeslot", read_only=True)

    # Report 8 #49: who cancelled (and why) so the counselee can rebook when
    # the counsellor cancelled.
    cancelled_by = serializers.SerializerMethodField()
    cancellation_reason = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return category_label(obj.category)

    def get_extra_kwargs(self):
        # Code review: counsellor/slot/category are fixed once booked — a
        # PATCH used to move the session without any slot bookkeeping (double
        # booking). Moves go through the reschedule endpoints.
        extra = super().get_extra_kwargs()
        if self.instance is not None:
            for name in ("counsellor", "timeslot", "category"):
                extra[name] = {**extra.get(name, {}), "read_only": True}
        return extra

    def validate_category(self, value):
        # Report 9 #105: an inactive category is hidden from new bookings; a
        # session that already has it keeps it.
        is_new = self.instance is None or self.instance.category_id != getattr(value, "id", None)
        if value is not None and not value.is_active and is_new:
            raise serializers.ValidationError("This counselling category is not available.")
        return value

    def get_cancelled_by(self, obj):
        c = getattr(obj, "cancellation", None) if obj.status == "cancelled" else None
        return c.cancelled_by if c else None

    def get_cancellation_reason(self, obj):
        c = getattr(obj, "cancellation", None) if obj.status == "cancelled" else None
        return c.reason if c else ""

    class Meta:
        model = CounselingSession
        fields = [
            "cancelled_by",
            "cancellation_reason",
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
            "meeting_link",
            "fee",
            "booked_at",
            "confirmed_at",
            "completed_at",
            "actual_start_at",
            "actual_end_at",
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
            # H16/D8 §2.3: only settable via the dedicated `meeting-link`
            # action (counsellor-only), never via a plain PATCH.
            "meeting_link",
            "fee",
            "booked_at",
            "confirmed_at",
            "completed_at",
            # D8: only settable via the `join`/`complete` actions.
            "actual_start_at",
            "actual_end_at",
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
            "refund_executed",
            "cancelled_at",
        ]
        read_only_fields = [
            "id",
            "refund_tier",
            "refund_amount",
            "refund_executed",
            "cancelled_at",
        ]


class SessionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionSummary
        fields = [
            "id",
            "session",
            "counsellor",
            # Report 3 §2.4 (6 fields)
            "client_details",
            "summary",
            "provisional_diagnosis",
            "case_prognosis",
            "session_smoothness",
            "smoothness_reason",
            "followup_recommended",
            # legacy
            "recommendations",
            "created_at",
        ]
        read_only_fields = ["id", "counsellor", "created_at"]


class SessionFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionFeedback
        fields = [
            "id",
            "session",
            "counselee",
            # Report 3 §2.2 (8 fields)
            "session_usefulness",
            "usefulness_text",
            "counsellor_empathy",
            "session_ending",
            "would_rechoose",
            "rechoose_text",
            "improvement_suggestions",
            "rating",  # 1-10 scale
            # legacy
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
