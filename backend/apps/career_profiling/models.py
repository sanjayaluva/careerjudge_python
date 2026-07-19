"""Models for the Career Profiling module.

Per SRS 05_profiling_configuration.json:
  - A Profiling Solution combines 2-3 assessments via data transformation
    (banding, mapping, ranking) and integration (match index computation)
  - The result is a career match index for each candidate

Models:
  - ProfilingSolution: the solution definition (title, purpose, description)
  - SelectedAssessment: links 2-3 assessments to a solution with a label
  - BandDefinition: per-assessment, per-variable band configuration
  - Band: individual band (range + code) within a BandDefinition
  - MappingCriterion: criterion band codes per career/role
  - MatchIndex: computed match score for a candidate
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProfilingSolution(models.Model):
    """A profiling solution that combines 2-3 assessments.

    Created by a psychometrician. Goes through:
    1. Solution definition (title, purpose, description, image)
    2. Assessment selection (2-3 published assessments)
    3. Data transformation (banding + mapping + ranking)
    4. Data integration (match index computation)
    """

    STATUS_CHOICES = [
        ("draft", "Draft (being configured)"),
        ("published", "Published (available for profiling)"),
        ("archived", "Archived"),
    ]

    title = models.CharField(_("title"), max_length=255)
    purpose = models.TextField(_("purpose"), blank=True)
    description = models.TextField(_("description"), blank=True)
    image = models.TextField(
        _("image"),
        blank=True,
        null=True,
        default="",
        help_text=_("Solution image as URL or base64 data URL."),
    )
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="draft")

    # Whether this solution includes a Polar assessment
    has_polar_assessment = models.BooleanField(
        _("has polar assessment"),
        default=False,
        help_text=_("If true, sub-variable band definition is required."),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="profiling_solutions",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("profiling solution")
        verbose_name_plural = _("profiling solutions")

    def __str__(self) -> str:
        return self.title


class SelectedAssessment(models.Model):
    """Links an assessment to a profiling solution with a label.

    Per SRS §3: at least 2, maximum 3 assessments must be selected.
    Each gets a label (e.g., 'CAT', 'CIA') used in reports.
    """

    solution = models.ForeignKey(
        ProfilingSolution, on_delete=models.CASCADE, related_name="selected_assessments"
    )
    assessment = models.ForeignKey(
        "assessment.Assessment", on_delete=models.CASCADE, related_name="profiling_solutions"
    )
    label = models.CharField(
        _("label"),
        max_length=50,
        help_text=_("Short name for this assessment in the solution (e.g., CAT, CIA)"),
    )
    is_polar = models.BooleanField(
        _("is polar"),
        default=False,
        help_text=_("If true, this assessment is a Polar-type assessment."),
    )
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = _("selected assessment")
        verbose_name_plural = _("selected assessments")
        unique_together = [("solution", "assessment")]

    def __str__(self) -> str:
        return f"{self.solution.title} > {self.label}"


class BandDefinition(models.Model):
    """Band definition for a specific variable (section) within an assessment.

    Per SRS §4.1.1:
      - At least 2 variables must be selected per assessment
      - Min 2 bands, Max 10 bands per variable
      - Band range is 0-100 (percentage)
      - Bands must not overlap
    """

    selected_assessment = models.ForeignKey(
        SelectedAssessment, on_delete=models.CASCADE, related_name="band_definitions"
    )
    section = models.ForeignKey(
        "assessment.AssessmentSection",
        on_delete=models.CASCADE,
        related_name="band_definitions",
        help_text=_("The variable (section) this band definition applies to."),
    )

    class Meta:
        ordering = ["selected_assessment__order", "section__level", "section__order"]
        verbose_name = _("band definition")
        verbose_name_plural = _("band definitions")
        unique_together = [("selected_assessment", "section")]

    def __str__(self) -> str:
        return f"{self.selected_assessment.label} > {self.section.title}"


class Band(models.Model):
    """An individual band within a band definition.

    Each band has a range (0-100) and a code (e.g., 'ANH1', 'ARM').
    Bands must not overlap.
    """

    band_definition = models.ForeignKey(
        BandDefinition, on_delete=models.CASCADE, related_name="bands"
    )
    band_number = models.PositiveIntegerField(
        _("band number"), help_text=_("1-based index within the definition")
    )
    range_min = models.FloatField(
        _("range min"), default=0, help_text=_("Lower bound (0-100, inclusive)")
    )
    range_max = models.FloatField(
        _("range max"), default=100, help_text=_("Upper bound (0-100, inclusive)")
    )
    band_code = models.CharField(
        _("band code"), max_length=20, help_text=_("Short code (e.g., ANH1, ARM)")
    )

    # For Polar assessments only: sub-variable bands
    sub_variable_name = models.CharField(
        _("sub-variable name"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("For Polar assessments: the sub-variable name for this band."),
    )

    class Meta:
        ordering = ["band_number"]
        verbose_name = _("band")
        verbose_name_plural = _("bands")

    def __str__(self) -> str:
        return f"{self.band_code} ({self.range_min}-{self.range_max})"

    def contains_percentage(self, percentage: float) -> bool:
        """Check if a percentage falls within this band's range."""
        return self.range_min <= percentage <= self.range_max


class MappingCriterion(models.Model):
    """Criterion band codes for a career/role per variable.

    Per SRS §4.1.2: the psychometrician defines which band code is the
    'criterion' (ideal) for each variable for a specific career/role.
    Used to compute the mapping score (how well the candidate matches).
    """

    solution = models.ForeignKey(
        ProfilingSolution, on_delete=models.CASCADE, related_name="mapping_criteria"
    )
    career_title = models.CharField(
        _("career title"), max_length=255, help_text=_("e.g., 'Computer Programmer'")
    )
    section = models.ForeignKey(
        "assessment.AssessmentSection",
        on_delete=models.CASCADE,
        related_name="mapping_criteria",
        help_text=_("The variable (section) this criterion applies to."),
    )
    criterion_band_code = models.CharField(
        _("criterion band code"),
        max_length=20,
        help_text=_("The ideal band code for this variable (e.g., 'ANH1')"),
    )
    weight = models.FloatField(
        _("weight"),
        default=1.0,
        help_text=_("Weight for this variable in the match index (default 1.0)"),
    )

    class Meta:
        ordering = ["career_title", "section__level", "section__order"]
        verbose_name = _("mapping criterion")
        verbose_name_plural = _("mapping criteria")
        unique_together = [("solution", "career_title", "section")]

    def __str__(self) -> str:
        return f"{self.career_title} > {self.section.title} = {self.criterion_band_code}"


class MatchIndex(models.Model):
    """Computed match index for a candidate against a career in a solution.

    Per SRS §5: the match index is computed by:
    1. Getting the candidate's band code for each variable
    2. Comparing with the criterion band code
    3. Computing a mapping score (5 = exact match, decreasing for distance)
    4. Aggregating into a Variable Mapping Index (VMI) and Final Match Index (FMI)
    """

    solution = models.ForeignKey(
        ProfilingSolution, on_delete=models.CASCADE, related_name="match_indices"
    )
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="match_indices",
    )
    career_title = models.CharField(_("career title"), max_length=255)

    # Computed values
    variable_mapping_index = models.FloatField(
        _("variable mapping index (VMI)"),
        null=True,
        blank=True,
        help_text=_("Average mapping score across all variables (0-100)"),
    )
    final_match_index = models.FloatField(
        _("final match index (FMI)"),
        null=True,
        blank=True,
        help_text=_("Final match score (0-100, higher = better match)"),
    )

    # Detailed breakdown stored as JSON
    variable_details = models.JSONField(
        _("variable details"),
        null=True,
        blank=True,
        help_text=_("Per-variable breakdown: band codes, mapping scores, etc."),
    )

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-final_match_index"]
        verbose_name = _("match index")
        verbose_name_plural = _("match indices")
        unique_together = [("solution", "candidate", "career_title")]

    def __str__(self) -> str:
        return (
            f"{self.candidate.email} - {self.career_title} "
            f"(FMI: {self.final_match_index or '?'})"
        )
