"""Models for the question_bank module.

Per SRS use cases UC010-UC017, UC025-UC026 + specs:
- 00_django_model_hints.json (model structure)
- 00_question_types_spec.json (21 question types)
- 00_scoring_rules.json (8 scoring modes)
- 01_question_bank_creation.json (review workflow)

Review workflow (3 stages):
  1. SME creates question (status: draft)
  2. Reviewer reviews content (status: pending_content_review → content_reviewed or sent_back)
  3. Psychometrician reviews psychometric properties (status: pending_psychometric_review → confirmed or sent_back)
  4. Confirmed questions are added to the Question Bank (status: active)
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

# ---------------------------------------------------------------------------
# Category (UC010, UC011, UC012)
# ---------------------------------------------------------------------------


class Category(models.Model):
    """Question bank category/sub-category (UC010).

    Supports unlimited nesting via parent FK.
    Created by Psychometrician, deleted by CJ Admin (with permission).
    """

    name = models.CharField(_("name"), max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="subcategories",
        null=True,
        blank=True,
        help_text=_("Parent category. NULL = top-level category."),
    )
    description = models.TextField(_("description"), blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_categories",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self) -> str:
        return self.name

    @property
    def full_path(self) -> str:
        """Returns full path like 'Parent > Child > Grandchild'."""
        parts = [self.name]
        node = self.parent
        while node:
            parts.append(node.name)
            node = node.parent
        return " > ".join(reversed(parts))


# ---------------------------------------------------------------------------
# Question (UC013, UC016, UC017) — supports 21 question types
# ---------------------------------------------------------------------------


class Question(models.Model):
    """A question in the question bank. Supports 21 question types.

    Question types (from 00_question_types_spec.json):
      MCQ variants: 1a-1h (text/image, audio, video, flash, passage, image display)
      FITB variants: 2a-2d (single, multi-field, word flash, image flash)
      Match Following: 3
      Grid List Selection: 4
      Hotspot: 5a (single), 5b (multi)
      Rank: 6a (simple), 6b (then rate)
      Rating: 7
      Forced Choice: 8a (single level), 8b (two level)

    Review workflow:
      draft → pending_content_review → content_reviewed → pending_psychometric_review
              → confirmed → active
      At any review stage: can be sent_back to previous stage
    """

    QUESTION_TYPE_CHOICES = [
        ("MCQ_TEXT_IMAGE", "1a: MCQ - Text/Image"),
        ("MCQ_TEXT_IMAGE_IMG_OPTIONS", "1b: MCQ - Text/Image with Image Options"),
        ("MCQ_AUDIO_MULTI", "1c: MCQ - Audio with Multiple Questions"),
        ("MCQ_VIDEO_MULTI", "1d: MCQ - Video with Multiple Questions"),
        ("MCQ_WORD_FLASH_MULTI", "1e: MCQ - Word Flash with Multiple Questions"),
        ("MCQ_IMAGE_FLASH_MULTI", "1f: MCQ - Image Flash with Multiple Questions"),
        ("MCQ_PASSAGE_DISPLAY_MULTI", "1g: MCQ - Passage Display with Multiple Questions"),
        ("MCQ_IMAGE_DISPLAY_MULTI", "1h: MCQ - Image Display with Multiple Questions"),
        ("FITB_SINGLE", "2a: FITB - Single Field"),
        ("FITB_MULTI_FIELD", "2b: FITB - Multiple Fields"),
        ("FITB_WORD_FLASH_MULTI", "2c: FITB - Word Flash with Multiple Recall Fields"),
        ("FITB_IMAGE_FLASH_MULTI", "2d: FITB - Image Flash with Multiple Recall Fields"),
        ("MATCH_FOLLOWING", "3: Match-the-Following"),
        ("GRID_LIST_SELECTION", "4: Grid-List Selection"),
        ("HOTSPOT_SINGLE", "5a: Hotspot - Single Answer"),
        ("HOTSPOT_MULTI", "5b: Hotspot - Multiple Answers"),
        ("RANK_SIMPLE", "6a: Simple Ranking Scale"),
        ("RANK_THEN_RATE", "6b: First Rank-Then Rate Scale"),
        ("STANDARD_RATING_SCALE", "7: Standard Rating Scale"),
        ("FORCED_CHOICE_SINGLE_LEVEL", "8a: Forced-Choice - Single Level"),
        ("FORCED_CHOICE_TWO_LEVEL", "8b: Forced-Choice - Two-Level"),
    ]

    SCORING_TYPE_CHOICES = [
        ("BINARY", "Binary Scoring (0 or 1)"),
        ("BINARY_FUZZY", "Binary with Fuzzy/Percentage Match"),
        ("PARTIAL", "Partial Credit Scoring"),
        ("NEGATIVE", "Negative Marking"),
        ("RANK", "Rank Scoring"),
        ("RANK_RATE", "Rank-then-Rate Scoring"),
        ("RATING", "Rating Scale Scoring"),
        ("FORCED_CHOICE", "Forced-Choice Scoring"),
        ("FORCED_CHOICE_RATED", "Forced-Choice Two-Level Scoring"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft (SME editing)"),
        ("pending_content_review", "Pending Content Review (Reviewer)"),
        ("content_reviewed", "Content Reviewed (Approved by Reviewer)"),
        ("pending_psychometric_review", "Pending Psychometric Review (Psychometrician)"),
        ("confirmed", "Confirmed (Added to Question Bank)"),
        ("sent_back", "Sent Back (Needs revision)"),
        ("rejected", "Rejected"),
        ("inactive", "Inactive"),
    ]

    # --- Core fields ---
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, related_name="questions", null=True, blank=True
    )
    question_type = models.CharField(
        _("question type"), max_length=50, choices=QUESTION_TYPE_CHOICES
    )
    question_id_label = models.CharField(
        _("question ID label"), max_length=50, blank=True, help_text="Display ID shown to candidate"
    )
    question_title = models.CharField(
        _("question title"),
        max_length=255,
        help_text=_("Short title that identifies this question in lists and previews. Required."),
    )
    question_text_1 = models.TextField(_("question text 1"))
    question_text_2 = models.TextField(_("question text 2"), blank=True)
    image = models.TextField(
        _("image"),
        blank=True,
        null=True,
        default="",
        help_text=_("Question image as an external URL or base64 data URL."),
    )
    image_width = models.PositiveIntegerField(
        _("image width (px)"),
        null=True,
        blank=True,
        help_text=_("Width of the image when hotspot shapes were drawn. Used to scale shapes."),
    )
    image_height = models.PositiveIntegerField(
        _("image height (px)"),
        null=True,
        blank=True,
        help_text=_("Height of the image when hotspot shapes were drawn. Used to scale shapes."),
    )
    order = models.PositiveIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    # --- Scoring configuration ---
    scoring_type = models.CharField(
        _("scoring type"), max_length=30, choices=SCORING_TYPE_CHOICES, default="BINARY"
    )
    case_sensitive = models.BooleanField(
        _("case sensitive"), default=False, help_text="For FITB types"
    )
    pct_match_threshold = models.FloatField(
        _("percentage match threshold"),
        null=True,
        blank=True,
        help_text="For FITB fuzzy match (0-100)",
    )

    # --- Type-specific configuration ---
    display_duration_seconds = models.PositiveIntegerField(
        _("display duration (seconds)"),
        null=True,
        blank=True,
        help_text="For timed display types 1g/1h",
    )
    flash_interval_ms = models.PositiveIntegerField(
        _("flash interval (ms)"), null=True, blank=True, help_text="For flash types 1e/1f/2c/2d"
    )
    flash_display_count = models.PositiveIntegerField(
        _("flash display count"), null=True, blank=True
    )
    flash_order = models.CharField(
        _("flash order"),
        max_length=10,
        choices=[("SEQUENCE", "Sequence (as entered)"), ("RANDOM", "Random (shuffled)")],
        default="SEQUENCE",
        help_text="For flash types 1e/1f/2c/2d — order in which flash items are presented",
    )
    grid_rows = models.PositiveIntegerField(
        _("grid rows"), null=True, blank=True, help_text="For type 4"
    )
    grid_cols = models.PositiveIntegerField(
        _("grid columns"), null=True, blank=True, help_text="For type 4"
    )
    rating_scale_points = models.PositiveIntegerField(
        _("rating scale points"), null=True, blank=True, help_text="For types 6b/7/8b"
    )
    rating_direction = models.CharField(
        _("rating direction"),
        max_length=10,
        choices=[("FORWARD", "Forward"), ("REVERSE", "Reverse")],
        null=True,
        blank=True,
    )
    passage_title = models.CharField(
        _("passage title"), max_length=255, blank=True, help_text="For type 1g"
    )
    passage_body = models.TextField(_("passage body"), blank=True, help_text="For type 1g")

    # --- Review workflow ---
    status = models.CharField(_("status"), max_length=50, choices=STATUS_CHOICES, default="draft")
    exposure_limit = models.PositiveIntegerField(
        _("exposure limit"),
        null=True,
        blank=True,
        help_text="Max times question can be used before auto-deactivation (set by Psychometrician)",
    )
    exposure_count = models.PositiveIntegerField(_("exposure count"), default=0)

    # --- Psychometric properties (UC026) ---
    difficulty_level = models.CharField(
        _("difficulty level"), max_length=20, blank=True, help_text="E.g., Easy, Medium, Hard"
    )
    cognitive_level = models.CharField(
        _("cognitive level"),
        max_length=50,
        blank=True,
        help_text="E.g., Recall, Understanding, Application, Analysis",
    )
    discrimination_index = models.FloatField(
        _("discrimination index"),
        null=True,
        blank=True,
        help_text="How well the question discriminates between high/low performers (-1 to 1)",
    )

    # --- Audit ---
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_questions",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("question")
        verbose_name_plural = _("questions")

    def __str__(self) -> str:
        return f"{self.question_type}: {self.question_text_1[:60]}..."

    @property
    def can_be_edited(self) -> bool:
        """Question can only be edited when in draft or sent_back status."""
        return self.status in ("draft", "sent_back")

    @property
    def is_in_question_bank(self) -> bool:
        """Question is in the active question bank (confirmed or active)."""
        return self.status == "confirmed" and self.is_active


# ---------------------------------------------------------------------------
# Response Option (for MCQ, FITB, Match, Grid, Rank, Forced-Choice)
# ---------------------------------------------------------------------------


class ResponseOption(models.Model):
    """Answer option for various question types.

    For MCQ: is_correct marks the right answer(s).
    For FITB: text_value holds the answer text, CorrectAnswer holds alternatives.
    For Match: option_type MATCH_A/MATCH_B, match_pair_id links pairs.
    For Grid: option_type DRAG_POOL, is_correct marks correct placements.
    For Rank: option_type RANK, order defines the correct ranking.
    For Forced-Choice: option_type FORCED_CHOICE, predefined_score holds the score.
    """

    OPTION_TYPE_CHOICES = [
        ("TEXT", "Text Option"),
        ("IMAGE", "Image Option"),
        ("MATCH_A", "Match Group A Item"),
        ("MATCH_B", "Match Group B Item"),
        ("DRAG_POOL", "Drag Pool Item (Grid)"),
        ("RANK", "Rank Item"),
        ("FORCED_CHOICE", "Forced-Choice Item"),
    ]

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    sub_question_index = models.PositiveIntegerField(
        _("sub-question index"),
        default=0,
        help_text="For multi-sub-question types; 0 = main question",
    )
    option_type = models.CharField(
        _("option type"), max_length=20, choices=OPTION_TYPE_CHOICES, default="TEXT"
    )
    label = models.CharField(
        _("label"), max_length=100, blank=True, help_text="e.g. Option 1, Group A item 3"
    )
    text_value = models.TextField(_("text value"), blank=True)
    image_file = models.TextField(
        _("image file"),
        blank=True,
        null=True,
        default="",
        help_text=_("Option image as an external URL or base64 data URL."),
    )
    is_correct = models.BooleanField(
        _("is correct"), default=False, help_text="For MCQ, grid, hotspot etc."
    )
    match_pair_id = models.PositiveIntegerField(
        _("match pair ID"),
        null=True,
        blank=True,
        help_text="For match-the-following: links Group A item to correct Group B item",
    )
    predefined_score = models.FloatField(
        _("predefined score"), default=1.0, help_text="For forced-choice: may be 0,1,2,3 etc."
    )
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering = ["sub_question_index", "order"]
        verbose_name = _("response option")
        verbose_name_plural = _("response options")

    def __str__(self) -> str:
        return f"{self.question.id}.{self.sub_question_index}.{self.order}: {self.text_value[:40] or self.label}"


# ---------------------------------------------------------------------------
# Correct Answer (for FITB — multiple correct answers per field)
# ---------------------------------------------------------------------------


class CorrectAnswer(models.Model):
    """Multiple correct answer strings for FITB types (up to 5 per field)."""

    response_option = models.ForeignKey(
        ResponseOption, on_delete=models.CASCADE, related_name="correct_answers"
    )
    answer_text = models.CharField(_("answer text"), max_length=500)
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = _("correct answer")
        verbose_name_plural = _("correct answers")

    def __str__(self) -> str:
        return self.answer_text[:60]


# ---------------------------------------------------------------------------
# Media File (for audio/video question types 1c, 1d)
# ---------------------------------------------------------------------------


class MediaFile(models.Model):
    """Audio/video files for question types 1c and 1d."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="media_files")
    media_type = models.CharField(
        _("media type"), max_length=10, choices=[("AUDIO", "Audio"), ("VIDEO", "Video")]
    )
    file = models.TextField(
        _("file"),
        blank=True,
        default="",
        help_text=_("Media file URL (audio/video) — external URL or base64 data URL."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("media file")
        verbose_name_plural = _("media files")

    def __str__(self) -> str:
        return f"{self.media_type}: {self.file.name}"


# ---------------------------------------------------------------------------
# Flash Item (for flash question types 1e, 1f, 2c, 2d)
# ---------------------------------------------------------------------------


class FlashItem(models.Model):
    """Items in flash lists for types 1e/1f/2c/2d.

    A subset of these items is randomly selected and flashed during the assessment.
    The candidate must recall and answer.
    """

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="flash_items")
    item_type = models.CharField(
        _("item type"), max_length=10, choices=[("TEXT", "Text"), ("IMAGE", "Image")]
    )
    text_value = models.CharField(_("text value"), max_length=255, blank=True)
    image_file = models.TextField(
        _("image file"),
        blank=True,
        null=True,
        default="",
        help_text=_("Flash image as an external URL or base64 data URL."),
    )
    order = models.PositiveIntegerField(_("order"), default=0)
    is_in_display_pool = models.BooleanField(
        _("in display pool"),
        default=True,
        help_text="Whether this item can be randomly selected for display",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = _("flash item")
        verbose_name_plural = _("flash items")

    def __str__(self) -> str:
        return self.text_value or f"Image #{self.id}"


# ---------------------------------------------------------------------------
# Hotspot Area (for hotspot question types 5a, 5b)
# ---------------------------------------------------------------------------


class HotspotArea(models.Model):
    """Pixel-defined hotspot areas for types 5a/5b.

    The candidate clicks within the image; if the click falls inside a
    hotspot area, the answer is correct.

    Supports three shape types:
    - RECTANGLE: defined by x, y, width_px, height_px (bounding box)
    - CIRCLE: defined by x, y (center) and radius
    - POLYGON: defined by points (JSON array of {x, y} relative to image)

    is_correct marks this area as a correct answer zone (green) vs
    a distractor zone (red).
    """

    SHAPE_CHOICES = [
        ("RECTANGLE", "Rectangle"),
        ("CIRCLE", "Circle"),
        ("POLYGON", "Polygon"),
    ]

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="hotspot_areas")
    sub_question_index = models.PositiveIntegerField(_("sub-question index"), default=0)
    x = models.PositiveIntegerField(_("x"), help_text="Top-left x (rect) or center x (circle)")
    y = models.PositiveIntegerField(_("y"), help_text="Top-left y (rect) or center y (circle)")
    width_px = models.PositiveIntegerField(_("width (px)"), default=0)
    height_px = models.PositiveIntegerField(_("height (px)"), default=0)
    area_size_code = models.CharField(_("area size code"), max_length=10, blank=True)
    shape_type = models.CharField(
        _("shape type"), max_length=20, choices=SHAPE_CHOICES, default="RECTANGLE"
    )
    is_correct = models.BooleanField(_("is correct"), default=True)
    radius = models.PositiveIntegerField(_("radius (px)"), null=True, blank=True)
    points = models.JSONField(_("polygon points"), null=True, blank=True)

    class Meta:
        ordering = ["sub_question_index", "id"]
        verbose_name = _("hotspot area")
        verbose_name_plural = _("hotspot areas")

    def __str__(self) -> str:
        return f"Hotspot ({self.x},{self.y}) {self.width_px}x{self.height_px}"

    def contains_point(self, click_x: int, click_y: int) -> bool:
        """Check if a click point falls within this hotspot area."""
        return (
            self.x <= click_x <= self.x + self.width_px
            and self.y <= click_y <= self.y + self.height_px
        )


# ---------------------------------------------------------------------------
# Question Review (UC014, UC015 — review workflow)
# ---------------------------------------------------------------------------


class QuestionReview(models.Model):
    """A review action on a question (content review or psychometric review).

    Each review creates a QuestionReview record with:
    - reviewer (the user who reviewed)
    - review_type (content or psychometric)
    - action (approve, send_back, reject)
    - comment (reason/feedback)
    - rating (1-5 content quality rating)
    """

    REVIEW_TYPE_CHOICES = [
        ("content", "Content Review (Reviewer)"),
        ("psychometric", "Psychometric Review (Psychometrician)"),
    ]

    ACTION_CHOICES = [
        ("approve", "Approve"),
        ("send_back", "Send Back to Previous Stage"),
        ("reject", "Reject"),
    ]

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="question_reviews",
        null=True,
        blank=True,
    )
    review_type = models.CharField(_("review type"), max_length=20, choices=REVIEW_TYPE_CHOICES)
    action = models.CharField(_("action"), max_length=20, choices=ACTION_CHOICES)
    comment = models.TextField(_("comment"), blank=True, help_text="Feedback/reason for the action")
    rating = models.PositiveIntegerField(
        _("content quality rating"),
        null=True,
        blank=True,
        help_text="1-5 scale (set by reviewer/psychometrician)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("question review")
        verbose_name_plural = _("question reviews")

    def __str__(self) -> str:
        return f"{self.review_type} {self.action} on Q#{self.question_id} by {self.reviewer}"
