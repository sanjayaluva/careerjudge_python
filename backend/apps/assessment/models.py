"""Models for the Assessment module.

Per SRS:
  - 03_assessment_configuration.json (assessment definition, variable structure,
    question assignment, scoring, display parameters)
  - 00_scoring_rules.json (9 scoring modes with pseudocode)
  - 00_django_model_hints.json (model structure)

Models:
  - Assessment: test definition (title, objective, instructions, duration, rules)
  - AssessmentSection: hierarchical variable structure (Level 1-4)
  - AssessmentQuestion: links question bank questions to sections
  - AssessmentSession: candidate's attempt (active/suspended/completed)
  - QuestionAttempt: candidate's answer to one question (raw_answer JSON, score)
  - SectionScore: aggregated score per section per session
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Assessment(models.Model):
    """Assessment / Test definition (UC018, UC019).

    Created by cj_admin, corp_admin, or psychometrician.
    Contains title, objective, instructions, and configuration for
    delivery, navigation, timing, and attempt rules.
    """

    STATUS_CHOICES = [
        ("draft", "Draft (being configured)"),
        ("published", "Published (available for sessions)"),
        ("archived", "Archived (no new sessions)"),
    ]

    NAVIGATION_CHOICES = [
        ("FREE", "Free Navigation and Response Review"),
        ("PREV_SECTION", "Only Previous Section Backward Navigation"),
        ("NO_BACKWARD_SECTION", "No Backward/Forward Navigation (Section Level)"),
        ("NO_BACKWARD_QUESTION", "No Backward/Forward Navigation (Question Level)"),
    ]

    ATTEMPT_CHOICES = [
        ("MULTIPLE_RETAKE", "Multiple Retakes Allowed"),
        ("SINGLE_RETAKE", "Multiple Retakes Not Allowed"),
        ("MULTIPLE_SESSION", "Multiple Sessions Allowed"),
        ("SINGLE_SESSION", "Multiple Sessions Not Allowed"),
    ]

    TIMER_LEVEL_CHOICES = [
        ("assessment", "Assessment Level (Level 0)"),
        ("level1", "Level 1 (Section)"),
        ("level2", "Level 2 (Sub-section)"),
        ("level3", "Level 3"),
        ("level4", "Level 4"),
        ("question", "Question Level"),
    ]

    ASSESSMENT_TYPE_CHOICES = [
        (
            "normal",
            "Normal Assessment (aptitude/ability — MCQ, FITB, Match, Grid, Hotspot)",
        ),
        (
            "psychometric",
            "Psychometric Assessment (Rating, Rank, Rank-then-Rate, Forced-Choice)",
        ),
    ]

    title = models.CharField(_("title"), max_length=255)
    objective = models.TextField(_("objective"), blank=True)
    description = models.TextField(_("description"), blank=True)
    instructions = models.TextField(_("instructions"), blank=True)

    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="draft")

    # Assessment type — controls which question categories can be attached.
    # Per SRS 03_assessment_configuration.json §4.1 vs §4.2, normal and
    # psychometric questions cannot be mixed in the same assessment.
    assessment_type = models.CharField(
        _("assessment type"),
        max_length=20,
        choices=ASSESSMENT_TYPE_CHOICES,
        default="normal",
        help_text=_(
            "Determines which question categories can be attached. "
            "Normal assessments accept only normal questions (MCQ/FITB/Match/Grid/Hotspot); "
            "psychometric assessments accept only psychometric questions "
            "(Rating/Rank/Rank-then-Rate/Forced-Choice). Mixing is not allowed."
        ),
    )

    # Display parameters
    total_duration_seconds = models.PositiveIntegerField(
        _("total duration (seconds)"),
        null=True,
        blank=True,
        help_text=_("Total time for the assessment. NULL = no time limit."),
    )
    timer_level = models.CharField(
        _("timer level"),
        max_length=20,
        choices=TIMER_LEVEL_CHOICES,
        default="assessment",
        help_text=_("Level at which the timer operates. Only ONE level can have a timer."),
    )
    display_order = models.CharField(
        _("display order"),
        max_length=10,
        choices=[("RANDOM", "Random"), ("STATIC", "Static (as configured)")],
        default="STATIC",
    )

    # Navigation rules
    navigation_rule = models.CharField(
        _("navigation rule"),
        max_length=30,
        choices=NAVIGATION_CHOICES,
        default="FREE",
    )

    # Attempt rules
    attempt_rule = models.CharField(
        _("attempt rule"),
        max_length=20,
        choices=ATTEMPT_CHOICES,
        default="SINGLE_SESSION",
    )

    # Pay-for-test (PLT-3): price to attempt this assessment. 0 = free. When
    # > 0, a candidate must have a completed payment (Payment module
    # "assessment", item_id = this assessment) before a new session starts.
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("Price to attempt this assessment. 0 = free (no payment gate)."),
    )

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_assessments",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("assessment")
        verbose_name_plural = _("assessments")

    def __str__(self) -> str:
        return self.title

    def aggregate_duration_seconds(self):
        """Effective total time budget for the assessment (SRS §5.2).

        A timer is set at only ONE level. Level 0 (assessment) uses
        ``total_duration_seconds`` directly. For a lower level, the aggregate
        is the SUM of the timers set at that level across the assigned
        variables/questions — never double-counting a parent and its
        children, because only the configured ``timer_level`` contributes.

        Returns ``None`` when no timer is set (backward-compatible: behaves
        as an untimed assessment).
        """
        if self.timer_level in ("level1", "level2", "level3", "level4"):
            level_num = int(self.timer_level[-1])
            values = [
                d
                for d in self.sections.filter(level=level_num).values_list(
                    "duration_seconds", flat=True
                )
                if d
            ]
            return sum(values) if values else None
        if self.timer_level == "question":
            values = [
                d
                for d in AssessmentQuestion.objects.filter(
                    section__assessment=self, duration_seconds__isnull=False
                ).values_list("duration_seconds", flat=True)
                if d
            ]
            return sum(values) if values else None
        # Assessment level (Level 0) or any unhandled value.
        return self.total_duration_seconds


class AssessmentSection(models.Model):
    """Hierarchical variable structure within an assessment (SRS Section 3).

    Supports up to 4 levels of nesting via parent FK.
    Level 1 = top-level section (variable).
    Level 2-4 = sub-sections (sub-variables).
    """

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="sections")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="subsections",
        null=True,
        blank=True,
        help_text=_("Parent section. NULL = top-level (Level 1)."),
    )
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    level = models.PositiveIntegerField(
        _("level"),
        default=1,
        help_text=_("1-4. Level 1 = top-level variable, Level 4 = deepest sub-variable."),
    )
    order = models.PositiveIntegerField(_("order"), default=0)
    order_mode = models.CharField(
        _("order mode"),
        max_length=10,
        choices=[("STATIC", "Static (as configured)"), ("RANDOM", "Random")],
        default="STATIC",
        help_text=_(
            "ASM-5 / §5.1: delivery order of this section's questions — STATIC keeps "
            "the configured order; RANDOM shuffles them per session (per-level ordering)."
        ),
    )
    duration_seconds = models.PositiveIntegerField(
        _("duration (seconds)"),
        null=True,
        blank=True,
        help_text=_("Time for this section. Only used if timer_level matches this level."),
    )
    delivery_count = models.PositiveIntegerField(
        _("delivery count"),
        null=True,
        blank=True,
        help_text=_(
            "SRS §4.1.1 — number of assigned questions to actually present during "
            "delivery. Set on the last-level (leaf) variable that holds questions. "
            "If set and less than the assigned count, that many questions are "
            "selected at random per session. NULL (or >= assigned count) delivers all."
        ),
    )

    class Meta:
        ordering = ["level", "order"]
        verbose_name = _("assessment section")
        verbose_name_plural = _("assessment sections")

    def __str__(self) -> str:
        return f"{self.assessment.title} > {self.title} (L{self.level})"


class AssessmentQuestion(models.Model):
    """Links a question from the question bank to an assessment section.

    Each question is assigned to a specific section with:
    - Display order within the section
    - Score override (optional — if NULL, uses question's default scoring)
    - Sub-question index for multi-sub-question types (1c-1h)
    """

    section = models.ForeignKey(
        AssessmentSection, on_delete=models.CASCADE, related_name="questions"
    )
    question = models.ForeignKey(
        "question_bank.Question",
        on_delete=models.CASCADE,
        related_name="assessment_assignments",
    )
    order = models.PositiveIntegerField(_("order"), default=0)
    sub_question_index = models.PositiveIntegerField(_("sub-question index"), default=0)
    score_override = models.FloatField(
        _("score override"),
        null=True,
        blank=True,
        help_text=_("Override the default max score for this question in this assessment."),
    )
    duration_seconds = models.PositiveIntegerField(
        _("duration (seconds)"),
        null=True,
        blank=True,
        help_text=_("Per-question timer. Only used if timer_level='question'."),
    )

    class Meta:
        ordering = ["order"]
        verbose_name = _("assessment question")
        verbose_name_plural = _("assessment questions")
        unique_together = [("section", "question", "sub_question_index")]

    def __str__(self) -> str:
        return f"{self.section.title} > Q#{self.question_id} (order={self.order})"


class AssessmentSession(models.Model):
    """A candidate's attempt at an assessment (UC020).

    Tracks the start/end time, status (active/suspended/completed),
    and links to the candidate's individual question attempts.
    """

    STATUS_CHOICES = [
        ("active", "Active (in progress)"),
        ("suspended", "Suspended (can resume)"),
        ("completed", "Completed (submitted)"),
        ("abandoned", "Abandoned (timed out or force-quit)"),
    ]

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="sessions")
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_sessions",
    )
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(auto_now_add=True)
    suspended_at = models.DateTimeField(_("suspended at"), null=True, blank=True)
    resumed_at = models.DateTimeField(_("resumed at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)

    # Overall score (calculated on completion)
    total_score = models.FloatField(_("total score"), null=True, blank=True)
    max_score = models.FloatField(_("max score"), null=True, blank=True)
    percentage = models.FloatField(_("percentage"), null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = _("assessment session")
        verbose_name_plural = _("assessment sessions")

    def __str__(self) -> str:
        return f"{self.assessment.title} - {self.candidate.email} ({self.status})"


class QuestionAttempt(models.Model):
    """One candidate's answer to one question within a session (UC021).

    Stores the raw answer as JSON (flexible for all 21 question types),
    the calculated score, and the attempt status.
    """

    STATUS_CHOICES = [
        ("not_attempted", "Not Attempted"),
        ("attempted", "Attempted"),
        ("bookmarked", "Bookmarked (for review)"),
        ("skipped", "Skipped"),
    ]

    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name="question_attempts"
    )
    question = models.ForeignKey(
        "question_bank.Question",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    section = models.ForeignKey(
        AssessmentSection,
        on_delete=models.CASCADE,
        related_name="question_attempts",
        null=True,
        blank=True,
    )
    sub_question_index = models.PositiveIntegerField(_("sub-question index"), default=0)
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="not_attempted"
    )

    # Raw answer stored as JSON — flexible for all question types:
    # MCQ: {"selected_option_ids": [1, 3]}
    # FITB: {"answers": ["Paris", "France"]}
    # Match: {"pairs": [{"a_id": 1, "b_id": 3}, ...]}
    # Grid: {"selected_cells": [{"r": 0, "c": 1}, ...]}
    # Hotspot: {"clicks": [{"x": 150, "y": 200}]}
    # Rank: {"ranking": [3, 1, 4, 2]}
    # Rating: {"rating": 4}
    # Forced Choice: {"selected_option_id": 2, "rating": 5}
    raw_answer = models.JSONField(
        _("raw answer"),
        null=True,
        blank=True,
        help_text=_("Flexible JSON storage for all answer types."),
    )

    score = models.FloatField(_("score"), null=True, blank=True)
    max_score = models.FloatField(_("max score"), null=True, blank=True)
    answered_at = models.DateTimeField(_("answered at"), null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(
        _("time spent (seconds)"), null=True, blank=True
    )

    class Meta:
        ordering = ["section__order", "question__created_at"]
        verbose_name = _("question attempt")
        verbose_name_plural = _("question attempts")
        unique_together = [("session", "question", "sub_question_index")]

    def __str__(self) -> str:
        return f"Session #{self.session_id} - Q#{self.question_id} ({self.status})"


class SectionScore(models.Model):
    """Aggregated score per section per session (for reporting/profiling).

    Calculated when the session is completed. Feeds into:
    - General reports (aptitude/ability scores)
    - Profiling reports (RVS, VMI, PMI, FMI etc.)
    """

    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name="section_scores"
    )
    section = models.ForeignKey(AssessmentSection, on_delete=models.CASCADE, related_name="scores")
    raw_score = models.FloatField(_("raw score"), default=0)
    max_score = models.FloatField(_("max score"), default=0)
    percentage = models.FloatField(_("percentage"), null=True, blank=True)

    class Meta:
        ordering = ["section__level", "section__order"]
        verbose_name = _("section score")
        verbose_name_plural = _("section scores")
        unique_together = [("session", "section")]

    def __str__(self) -> str:
        return (
            f"Session #{self.session_id} - {self.section.title}: {self.raw_score}/{self.max_score}"
        )

    def save(self, *args, **kwargs):
        if self.max_score and self.max_score > 0:
            self.percentage = round((self.raw_score / self.max_score) * 100, 2)
        else:
            self.percentage = 0
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# AssessmentModificationRequest — non-admin requests admin approval to edit
# the title of, or delete, a PUBLISHED assessment. Per SRS
# 03_assessment_configuration.json §2.2/§2.3.
# ---------------------------------------------------------------------------


class AssessmentModificationRequest(models.Model):
    """Non-admin's request to edit the title of, or delete, a published assessment.

    Per SRS §2.2/§2.3: 'After going live, user cannot directly edit
    Assessment Title. An edit request is sent to Admin for approval.'
    Deletion of a published assessment follows the same request→approve
    pattern.
    """

    ACTION_CHOICES = [
        ("edit", "Edit Title"),
        ("delete", "Delete Assessment"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending Admin Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="modification_requests"
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_modification_requests",
    )
    action = models.CharField(_("action"), max_length=10, choices=ACTION_CHOICES)
    proposed_title = models.CharField(
        _("proposed title"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("New title requested (only for action='edit')."),
    )
    reason = models.TextField(_("reason"), help_text=_("Reason for the edit/delete request"))
    status = models.CharField(_("status"), max_length=10, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessment_modification_reviews",
    )
    review_comment = models.TextField(_("review comment"), blank=True, default="")
    reviewed_at = models.DateTimeField(_("reviewed at"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("assessment modification request")
        verbose_name_plural = _("assessment modification requests")

    def __str__(self) -> str:
        return f"{self.action} request for '{self.assessment.title}' ({self.status})"
