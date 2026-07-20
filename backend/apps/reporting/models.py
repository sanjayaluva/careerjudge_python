"""Models for the Reporting module.

Per SRS 04_general_report_generation.json:
  - Every assessment must have one or more reports
  - General report: based on a single assessment
  - Profiling report: based on multiple assessments (uses Career Profiling)
  - Report types: Descriptive, Typological, Interpretative, Group
  - Data inputs: Level0-4 + Question level, with statistical conversion
  - Descriptive: cutoffs per variable
  - Interpretative: band definitions per variable
  - Typological: code generation per variable
  - Polar: opposite variable computation

Per SRS 06_profiling_report_generation.json:
  - FMI (Final Match Index), PMI (Profile Match Index), VMI (Variable Match Index)
  - Each data input has its own band definition + table/graph layout

Models:
  - Report: report definition
  - ReportSection: layout sections
  - ReportCutoff: cutoff scores per variable (descriptive reports)
  - ReportBand: band definitions per variable (interpretative reports)
  - TypologicalCode: code generation per variable (typological reports)
  - PolarVariable: opposite variable definitions (polar assessments)
  - GeneratedReport: rendered output for a candidate session
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Report(models.Model):
    """A report definition linked to an assessment or profiling solution."""

    REPORT_TYPE_CHOICES = [
        ("descriptive", "Descriptive Report"),
        ("typological", "Typological Report"),
        ("interpretative", "Interpretative Report"),
        ("group", "Group Report"),
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

    DATA_INPUT_LEVEL_CHOICES = [
        ("level0", "Level 0 (entire assessment summary)"),
        ("level1", "Level 1 (all L1 variables)"),
        ("level2", "Level 2 (all L2 variables)"),
        ("level3", "Level 3 (all L3 variables)"),
        ("level4", "Level 4 (all L4 variables)"),
        ("question", "Question Level (per-question scores)"),
    ]

    STAT_CONVERSION_CHOICES = [
        ("percentage", "Percentage Score"),
        ("percentile", "Percentile Score"),
        ("sten", "STEN Score"),
        ("stenine", "STENINE Score"),
    ]

    # --- Core fields ---
    title = models.CharField(_("title"), max_length=255)
    objective = models.TextField(_("objective"), blank=True)
    description = models.TextField(_("description"), blank=True)

    report_type = models.CharField(
        _("report type"), max_length=20, choices=REPORT_TYPE_CHOICES, default="descriptive"
    )
    scope = models.CharField(_("scope"), max_length=20, choices=SCOPE_CHOICES, default="general")
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="draft")

    # --- Links ---
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

    # --- Data input configuration (SRS §2.3) ---
    data_input_level = models.CharField(
        _("data input level"),
        max_length=20,
        choices=DATA_INPUT_LEVEL_CHOICES,
        default="level1",
        help_text=_("Which level of summary scores to use in the report."),
    )
    stat_conversion = models.CharField(
        _("statistical conversion"),
        max_length=20,
        choices=STAT_CONVERSION_CHOICES,
        default="percentage",
        help_text=_("How raw scores are converted for display."),
    )

    # --- Layout flags ---
    include_score_summary = models.BooleanField(_("include score summary"), default=True)
    include_section_breakdown = models.BooleanField(_("include section breakdown"), default=True)
    include_question_analysis = models.BooleanField(_("include question analysis"), default=False)
    include_charts = models.BooleanField(_("include charts"), default=True)
    include_recommendations = models.BooleanField(_("include recommendations"), default=False)

    # --- Profiling report data inputs (SRS 06 §3) ---
    include_raw_summary = models.BooleanField(_("include raw summary"), default=True)
    include_fmi = models.BooleanField(_("include FMI report"), default=False)
    include_pmi = models.BooleanField(_("include PMI report"), default=False)
    include_vmi = models.BooleanField(_("include VMI report"), default=False)

    # --- Template / branding ---
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
    """A layout section within a report."""

    SECTION_TYPE_CHOICES = [
        ("header", "Header (title + logo)"),
        ("score_summary", "Score Summary (total + percentage)"),
        ("section_breakdown", "Section Breakdown (per-variable scores)"),
        ("question_analysis", "Question Analysis (per-question details)"),
        ("chart", "Chart (bar/pie/radar)"),
        ("narrative", "Narrative Text (descriptive/interpretative)"),
        ("cutoff_table", "Cutoff Table (descriptive)"),
        ("type_profile", "Type Profile (typological)"),
        ("band_table", "Band Table (interpretative)"),
        ("fmi_report", "FMI Report (profiling)"),
        ("pmi_report", "PMI Report (profiling)"),
        ("vmi_report", "VMI Report (profiling)"),
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
    # Table head / graph legend definitions (SRS §3.1.2, §3.2.2, §3.3.2)
    table_graph_config = models.JSONField(
        _("table/graph configuration"),
        null=True,
        blank=True,
        help_text=_("JSON with table_heads or graph_legends configuration."),
    )
    order = models.PositiveIntegerField(_("order"), default=0)
    is_visible = models.BooleanField(_("visible"), default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("report section")
        verbose_name_plural = _("report sections")

    def __str__(self) -> str:
        return f"{self.report.title} > {self.title or self.section_type} (order={self.order})"


class ReportCutoff(models.Model):
    """Cutoff scores per variable for descriptive reports (SRS §3.1.1).

    Defines:
      - cutoff_score: the threshold value
      - cutoff_label: label shown when score is above cutoff
      - above_description: text shown when candidate's score is above cutoff
      - below_description: text shown when candidate's score is below cutoff
    """

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="cutoffs")
    section = models.ForeignKey(
        "assessment.AssessmentSection",
        on_delete=models.CASCADE,
        related_name="report_cutoffs",
        help_text=_("The variable (section) this cutoff applies to."),
    )
    cutoff_score = models.FloatField(
        _("cutoff score"), help_text=_("Threshold value (in the selected conversion type)")
    )
    cutoff_label = models.CharField(_("cutoff label"), max_length=100, blank=True, default="")
    above_description = models.TextField(_("above cutoff description"), blank=True, default="")
    below_description = models.TextField(_("below cutoff description"), blank=True, default="")

    class Meta:
        ordering = ["section__level", "section__order"]
        verbose_name = _("report cutoff")
        verbose_name_plural = _("report cutoffs")
        unique_together = [("report", "section")]

    def __str__(self) -> str:
        return f"{self.report.title} > {self.section.title} (cutoff: {self.cutoff_score})"


class ReportBand(models.Model):
    """Band definitions per variable for interpretative reports (SRS §3.3.1).

    Each band has:
      - range_min / range_max: score range
      - band_label: label shown for this band (e.g., "High", "Medium", "Low")
      - description: interpretative text for this band
      - colour_code: optional colour for visual display
    """

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="bands")
    section = models.ForeignKey(
        "assessment.AssessmentSection",
        on_delete=models.CASCADE,
        related_name="report_bands",
        help_text=_("The variable (section) this band applies to."),
    )
    band_number = models.PositiveIntegerField(_("band number"), default=1)
    range_min = models.FloatField(_("range min"), default=0)
    range_max = models.FloatField(_("range max"), default=100)
    band_label = models.CharField(_("band label"), max_length=100, blank=True, default="")
    description = models.TextField(_("description"), blank=True, default="")
    colour_code = models.CharField(
        _("colour code"),
        max_length=20,
        blank=True,
        default="",
        help_text=_("Hex colour, e.g., #FF0000"),
    )

    class Meta:
        ordering = ["section__level", "section__order", "band_number"]
        verbose_name = _("report band")
        verbose_name_plural = _("report bands")

    def __str__(self) -> str:
        return f"{self.report.title} > {self.section.title} > Band {self.band_number}"

    def contains_score(self, score: float) -> bool:
        return self.range_min <= score <= self.range_max


class TypologicalCode(models.Model):
    """Code generation per variable for typological reports (SRS §3.2.1).

    The psychometrician assigns an alphabet or number to each variable.
    The top-scoring variables' codes are concatenated to form the candidate's
    personality/intellectual type profile.
    """

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="typological_codes")
    section = models.ForeignKey(
        "assessment.AssessmentSection",
        on_delete=models.CASCADE,
        related_name="typological_codes",
        help_text=_("The variable (section) this code applies to."),
    )
    code = models.CharField(
        _("code"),
        max_length=10,
        help_text=_("Alphabet or number for code generation (e.g., 'A', '1')"),
    )
    # How many top-scoring variables to include in the type profile
    top_n = models.PositiveIntegerField(
        _("top N variables"),
        default=3,
        help_text=_("Number of top-scoring variables to include in the type profile."),
    )

    class Meta:
        ordering = ["section__level", "section__order"]
        verbose_name = _("typological code")
        verbose_name_plural = _("typological codes")
        unique_together = [("report", "section")]

    def __str__(self) -> str:
        return f"{self.report.title} > {self.section.title} = {self.code}"


class PolarVariable(models.Model):
    """Polar variable definitions for polar assessments (SRS §4).

    For polar assessments, each variable has an opposite:
      - If candidate scores 85 on Extroversion, Introversion = 100 - 85 = 15
    """

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="polar_variables")
    section = models.ForeignKey(
        "assessment.AssessmentSection",
        on_delete=models.CASCADE,
        related_name="polar_variables",
        help_text=_("The primary variable."),
    )
    opposite_name = models.CharField(
        _("opposite variable name"),
        max_length=255,
        help_text=_(
            "Name of the opposite variable (e.g., 'Introversion' if primary is 'Extroversion')"
        ),
    )

    class Meta:
        ordering = ["section__level", "section__order"]
        verbose_name = _("polar variable")
        verbose_name_plural = _("polar variables")
        unique_together = [("report", "section")]

    def __str__(self) -> str:
        return f"{self.section.title} ↔ {self.opposite_name}"

    def compute_opposite_score(self, primary_score: float, max_score: float = 100.0) -> float:
        """Compute the opposite variable's score.

        Per SRS §4: Opposite = Max Score - Summary Score
        """
        return round(max_score - primary_score, 2)


class GeneratedReport(models.Model):
    """A generated report instance for a specific candidate session."""

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

    rendered_data = models.JSONField(
        _("rendered data"),
        null=True,
        blank=True,
        help_text=_("The computed report data: scores, charts, narratives, etc."),
    )

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
