"""Models for the Reporting module.

Per SRS 04_general_report_generation.json:
  - Every assessment must have one or more reports
  - General report: based on a single assessment
  - Profiling report: based on multiple assessments (uses Career Profiling)
  - Report types: Descriptive, Typological, Interpretative

Models:
  - Report: report definition (title, objective, type, linked assessment/solution)
  - ReportSection: layout sections within a report
  - ReportConfig: configuration for data inputs and display
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Report(models.Model):
    """A report definition linked to an assessment or profiling solution.

    Per SRS §2 (Parameter Setting & Description):
      - Define report title and objective
      - Add description
      - Define report type(s)
      - Define data inputs and report structure
    """

    REPORT_TYPE_CHOICES = [
        ("descriptive", "Descriptive Report"),
        ("typological", "Typological Report"),
        ("interpretative", "Interpretative Report"),
    ]

    SCOPE_CHOICES = [
        ("general", "General Report (single assessment)"),
        ("profiling", "Profiling Report (multiple assessments via profiling solution)"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft (being configured)"),
        ("published", "Published (available for generation)"),
        ("archived", "Archived"),
    ]

    title = models.CharField(_("title"), max_length=255)
    objective = models.TextField(_("objective"), blank=True)
    description = models.TextField(_("description"), blank=True)

    report_type = models.CharField(
        _("report type"), max_length=20, choices=REPORT_TYPE_CHOICES, default="descriptive"
    )
    scope = models.CharField(_("scope"), max_length=20, choices=SCOPE_CHOICES, default="general")
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="draft")

    # Link to either a single assessment (general) or a profiling solution (profiling)
    assessment = models.ForeignKey(
        "assessment.Assessment",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
        help_text=_("For general reports: the assessment this report is based on."),
    )
    profiling_solution = models.ForeignKey(
        "career_profiling.ProfilingSolution",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
        help_text=_("For profiling reports: the solution this report is based on."),
    )

    # Report layout configuration
    include_score_summary = models.BooleanField(_("include score summary"), default=True)
    include_section_breakdown = models.BooleanField(_("include section breakdown"), default=True)
    include_question_analysis = models.BooleanField(_("include question analysis"), default=False)
    include_charts = models.BooleanField(_("include charts"), default=True)
    include_recommendations = models.BooleanField(_("include recommendations"), default=False)

    # Template / branding
    header_text = models.CharField(_("header text"), max_length=255, blank=True, default="")
    footer_text = models.CharField(_("footer text"), max_length=255, blank=True, default="")
    logo = models.TextField(_("logo"), blank=True, null=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reports",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("report")
        verbose_name_plural = _("reports")

    def __str__(self) -> str:
        return self.title


class ReportSection(models.Model):
    """A layout section within a report.

    Per SRS §4 (Report Layout): reports are composed of sections that
    display different types of data (scores, charts, narratives, etc.).
    """

    SECTION_TYPE_CHOICES = [
        ("header", "Header (title + logo)"),
        ("score_summary", "Score Summary (total + percentage)"),
        ("section_breakdown", "Section Breakdown (per-variable scores)"),
        ("question_analysis", "Question Analysis (per-question details)"),
        ("chart", "Chart (bar/pie/radar)"),
        ("narrative", "Narrative Text (descriptive/interpretative)"),
        ("recommendation", "Recommendations"),
        ("footer", "Footer"),
        ("custom", "Custom Content"),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="sections")
    section_type = models.CharField(
        _("section type"), max_length=20, choices=SECTION_TYPE_CHOICES, default="custom"
    )
    title = models.CharField(_("title"), max_length=255, blank=True, default="")
    content = models.TextField(
        _("content"),
        blank=True,
        default="",
        help_text=_("For narrative sections: the text content. For charts: JSON config."),
    )
    order = models.PositiveIntegerField(_("order"), default=0)
    is_visible = models.BooleanField(_("visible"), default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("report section")
        verbose_name_plural = _("report sections")

    def __str__(self) -> str:
        return f"{self.report.title} > {self.title or self.section_type} (order={self.order})"


class GeneratedReport(models.Model):
    """A generated report instance for a specific candidate session.

    Created when a report is 'generated' for a completed assessment session.
    Stores the rendered data so it can be viewed multiple times without
    re-computing.
    """

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="generated_reports")
    session = models.ForeignKey(
        "assessment.AssessmentSession",
        on_delete=models.CASCADE,
        related_name="generated_reports",
    )
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_reports",
    )

    # Rendered data (JSON)
    rendered_data = models.JSONField(
        _("rendered data"),
        null=True,
        blank=True,
        help_text=_("The computed report data: scores, charts, narratives, etc."),
    )

    # Status
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=[("generated", "Generated"), ("failed", "Failed")],
        default="generated",
    )
    error_message = models.TextField(_("error message"), blank=True, default="")

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = _("generated report")
        verbose_name_plural = _("generated reports")
        unique_together = [("report", "session")]

    def __str__(self) -> str:
        return f"{self.report.title} - {self.candidate.email}"
