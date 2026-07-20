"""Serializers for the question_bank module."""

from rest_framework import serializers

from .models import (
    Category,
    CorrectAnswer,
    FlashItem,
    HotspotArea,
    MediaFile,
    Question,
    QuestionReview,
    ResponseOption,
)

# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------


class CategorySerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source="questions.count", read_only=True)
    subcategory_count = serializers.IntegerField(source="subcategories.count", read_only=True)
    full_path = serializers.CharField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "parent",
            "description",
            "is_active",
            "question_count",
            "subcategory_count",
            "full_path",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Lighter serializer for tree views (no counts)."""

    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "parent", "description", "is_active", "subcategories"]

    def get_subcategories(self, obj):
        children = obj.subcategories.filter(is_active=True).order_by("name")
        return CategoryTreeSerializer(children, many=True).data


# ---------------------------------------------------------------------------
# Nested serializers for Question children
# ---------------------------------------------------------------------------


class CorrectAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectAnswer
        fields = ["id", "answer_text", "order"]
        read_only_fields = ["id"]


class ResponseOptionSerializer(serializers.ModelSerializer):
    correct_answers = CorrectAnswerSerializer(many=True, read_only=True)
    # Allow image_file to be passed as a URL string, base64 data URL, or None.
    # to_internal_value converts None → "" so the DB never sees NULL (avoids
    # IntegrityError if the column is NOT NULL, and avoids needing null=True
    # on the model field — which is the Django convention for text fields).
    image_file = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, default=""
    )

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        # Normalize None → "" for image_file (Django convention: empty string, not NULL)
        if ret.get("image_file") is None:
            ret["image_file"] = ""
        return ret

    class Meta:
        model = ResponseOption
        fields = [
            "id",
            "sub_question_index",
            "option_type",
            "label",
            "text_value",
            "image_file",
            "is_correct",
            "match_pair_id",
            "predefined_score",
            "order",
            "correct_answers",
        ]
        read_only_fields = ["id", "correct_answers"]


class MediaFileSerializer(serializers.ModelSerializer):
    # Allow file to be passed as a URL string or base64 data URL
    file = serializers.CharField(allow_blank=False, allow_null=False)

    class Meta:
        model = MediaFile
        fields = ["id", "media_type", "file", "created_at"]
        read_only_fields = ["id", "created_at"]


class FlashItemSerializer(serializers.ModelSerializer):
    # Allow image_file to be passed as a URL string, base64 data URL, or None.
    # to_internal_value converts None → "" so the DB never sees NULL.
    image_file = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, default=""
    )

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        if ret.get("image_file") is None:
            ret["image_file"] = ""
        return ret

    class Meta:
        model = FlashItem
        fields = ["id", "item_type", "text_value", "image_file", "order", "is_in_display_pool"]
        read_only_fields = ["id"]


class HotspotAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotspotArea
        fields = [
            "id",
            "sub_question_index",
            "x",
            "y",
            "width_px",
            "height_px",
            "area_size_code",
            "shape_type",
            "is_correct",
            "radius",
            "points",
        ]
        read_only_fields = ["id"]


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------


class QuestionListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views (no image — base64 data URLs would bloat list responses)."""

    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    question_type_label = serializers.CharField(source="get_question_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    scoring_type_label = serializers.CharField(source="get_scoring_type_display", read_only=True)
    is_psychometric = serializers.BooleanField(read_only=True)
    question_category = serializers.CharField(read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "question_type",
            "question_type_label",
            "question_id_label",
            "question_title",
            "question_text_1",
            "category",
            "category_name",
            "status",
            "status_label",
            "scoring_type",
            "scoring_type_label",
            "difficulty_level",
            "cognitive_level",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "is_active",
            "exposure_count",
            "is_psychometric",
            "question_category",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "exposure_count",
            "is_psychometric",
            "question_category",
        ]


class QuestionDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested children for detail/create/update views."""

    # Allow image to be a URL string or base64 data URL (read-only here; created via QuestionCreateSerializer)
    image = serializers.CharField(read_only=True)

    options = ResponseOptionSerializer(many=True, read_only=True)
    media_files = MediaFileSerializer(many=True, read_only=True)
    flash_items = FlashItemSerializer(many=True, read_only=True)
    hotspot_areas = HotspotAreaSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    question_type_label = serializers.CharField(source="get_question_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    is_psychometric = serializers.BooleanField(read_only=True)
    question_category = serializers.CharField(read_only=True)
    validation_warnings = serializers.SerializerMethodField()
    ready_for_review = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "category",
            "category_name",
            "question_type",
            "question_type_label",
            "question_id_label",
            "question_title",
            "question_text_1",
            "question_text_2",
            "image",
            "image_width",
            "image_height",
            "order",
            "is_active",
            "scoring_type",
            "case_sensitive",
            "pct_match_threshold",
            "display_duration_seconds",
            "flash_interval_ms",
            "flash_display_count",
            "flash_order",
            "grid_rows",
            "grid_cols",
            "rating_scale_points",
            "rating_direction",
            "passage_title",
            "passage_body",
            "status",
            "status_label",
            "exposure_limit",
            "exposure_count",
            "difficulty_level",
            "cognitive_level",
            "discrimination_index",
            "is_psychometric",
            "question_category",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            # Nested children
            "options",
            "media_files",
            "flash_items",
            "hotspot_areas",
            "reviews",
            "validation_warnings",
            "ready_for_review",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "exposure_count",
            "is_psychometric",
            "question_category",
            "options",
            "media_files",
            "flash_items",
            "hotspot_areas",
            "reviews",
        ]

    def get_reviews(self, obj):
        reviews = obj.reviews.select_related("reviewer").all()
        return QuestionReviewSerializer(reviews, many=True).data

    def get_validation_warnings(self, obj):
        from .validation import validate_question_config

        return validate_question_config(obj)

    def get_ready_for_review(self, obj):
        from .validation import question_is_ready_for_review

        return question_is_ready_for_review(obj)


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions (SME creates with draft status)."""

    # Allow image to be passed as a URL string, base64 data URL, or None.
    # to_internal_value converts None → "" so the DB never sees NULL.
    image = serializers.CharField(allow_blank=True, allow_null=True, required=False, default="")

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        if ret.get("image") is None:
            ret["image"] = ""
        return ret

    class Meta:
        model = Question
        fields = [
            "category",
            "question_type",
            "question_id_label",
            "question_title",
            "question_text_1",
            "question_text_2",
            "image",
            "image_width",
            "image_height",
            "scoring_type",
            "case_sensitive",
            "pct_match_threshold",
            "display_duration_seconds",
            "flash_interval_ms",
            "flash_display_count",
            "flash_order",
            "grid_rows",
            "grid_cols",
            "rating_scale_points",
            "rating_direction",
            "passage_title",
            "passage_body",
            "difficulty_level",
            "cognitive_level",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user:
            validated_data["created_by"] = request.user
        validated_data.setdefault("status", "draft")
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Question Review
# ---------------------------------------------------------------------------


class QuestionReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True, default=None)
    review_type_label = serializers.CharField(source="get_review_type_display", read_only=True)
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = QuestionReview
        fields = [
            "id",
            "question",
            "reviewer",
            "reviewer_name",
            "review_type",
            "review_type_label",
            "action",
            "action_label",
            "comment",
            "rating",
            "created_at",
        ]
        read_only_fields = ["id", "reviewer", "created_at"]


class QuestionReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a review action (approve/send_back/reject)."""

    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())

    class Meta:
        model = QuestionReview
        fields = ["question", "review_type", "action", "comment", "rating"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user:
            validated_data["reviewer"] = request.user

        review = super().create(validated_data)

        # Update question status based on review action
        question = validated_data["question"]  # This is now a Question object
        action = validated_data["action"]
        review_type = validated_data["review_type"]

        if action == "approve":
            if review_type == "content":
                question.status = "content_reviewed"
            elif review_type == "psychometric":
                question.status = "confirmed"
                question.is_active = True
        elif action == "send_back":
            question.status = "sent_back"
        elif action == "reject":
            question.status = "rejected"
            question.is_active = False

        question.save()
        return review
