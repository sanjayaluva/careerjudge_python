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

    Per SRS §4.1.4: each criterion also carries career metadata (stream,
    code, description) and, when the rank system is enabled for the
    selected assessment, a rank_order (1..N) that indexes into the
    RankDefinition chart to look up the rank_value used as the weight
    in the VMI/PMI computation.
    """

    solution = models.ForeignKey(
        ProfilingSolution, on_delete=models.CASCADE, related_name="mapping_criteria"
    )
    # --- Career metadata (SRS §4.1.4) ---
    career_stream = models.CharField(
        _("career stream"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("e.g., 'IT Sector' — groups careers in reports."),
    )
    career_title = models.CharField(
        _("career title"), max_length=255, help_text=_("e.g., 'Computer Programmer'")
    )
    career_code = models.CharField(
        _("career code"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("Short code (e.g., 'ITCP')"),
    )
    career_description = models.TextField(_("career description"), blank=True, default="")

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
    # --- Rank system (SRS §4.1.3 + §4.1.4) ---
    # When the parent selected_assessment has a RankDefinition, this rank_order
    # (1..N) is used to look up the rank_value from the chart. The rank_value
    # is then used as the weight in VMI/PMI. When no RankDefinition exists
    # (unranked mode), the legacy `weight` field is used directly (default 1.0).
    rank_order = models.PositiveIntegerField(
        _("rank order"),
        null=True,
        blank=True,
        help_text=_(
            "Rank order (1..N) into the RankDefinition chart. "
            "Leave null when the assessment has no rank system defined."
        ),
    )
    weight = models.FloatField(
        _("weight (legacy / unranked mode)"),
        default=1.0,
        help_text=_(
            "Weight for this variable in the match index. Used only when "
            "rank_order is null (unranked mode). Ignored when a RankDefinition "
            "exists for the parent selected_assessment."
        ),
    )

    class Meta:
        ordering = ["career_stream", "career_title", "section__level", "section__order"]
        verbose_name = _("mapping criterion")
        verbose_name_plural = _("mapping criteria")
        # A criterion is unique per (solution, career, section). career_stream
        # is included so the same career_title can exist under different
        # streams (e.g., 'Analyst' in IT vs Finance).
        unique_together = [
            ("solution", "career_stream", "career_title", "section"),
        ]

    def __str__(self) -> str:
        return f"{self.career_title} > {self.section.title} = {self.criterion_band_code}"


class RankDefinition(models.Model):
    """Rank Order Chart for a selected assessment (SRS §4.1.3 — OPTIONAL).

    Per SRS §4.1.3: the psychometrician defines a chart with N rank values
    (one per variable, where N = number of variables). Rank1 receives the
    max value (e.g., 2.0) and RankN the lowest (e.g., 1.0).

    The MappingCriterion.rank_order (1..N) on each criterion indexes into
    this chart to look up the rank_value, which is then used as the weight
    in VMI/PMI computation:

        product_score = mapping_score x rank_value
        max_product    = MAX_MAPPING_SCORE x rank_value
        VMI            = (product_score / max_product) x 100

    For Polar assessments (SRS §4.2.3), this chart is NOT optional and the
    rank_value depends on BOTH the rank_order AND the match_code (HM/MM/LM)
    from the criterion-vs-user band comparison — see PolarRankValue.
    """

    selected_assessment = models.OneToOneField(
        SelectedAssessment,
        on_delete=models.CASCADE,
        related_name="rank_definition",
    )
    is_polar = models.BooleanField(
        _("is polar rank chart"),
        default=False,
        help_text=_(
            "If true, rank values are looked up by (match_code, rank_order) "
            "via PolarRankValue. If false, by rank_order alone via RankValue."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("rank definition")
        verbose_name_plural = _("rank definitions")

    def __str__(self) -> str:
        return f"Rank chart for {self.selected_assessment.label}"


class RankValue(models.Model):
    """A single entry in the standard (non-polar) Rank Order Chart.

    Per SRS §4.1.3 sample: Rank1=2.0, Rank2=1.8, Rank3=1.6, Rank4=1.4,
    Rank5=1.2, Rank6=1.0. Rank1 receives the max value.
    """

    rank_definition = models.ForeignKey(
        RankDefinition, on_delete=models.CASCADE, related_name="rank_values"
    )
    rank_order = models.PositiveIntegerField(
        _("rank order"),
        help_text=_("1-based position in the chart (Rank1, Rank2, ...)"),
    )
    rank_value = models.FloatField(
        _("rank value"),
        help_text=_("The weight applied when this rank is selected (e.g., 2.0)"),
    )

    class Meta:
        ordering = ["rank_order"]
        verbose_name = _("rank value")
        verbose_name_plural = _("rank values")
        unique_together = [("rank_definition", "rank_order")]

    def __str__(self) -> str:
        return f"Rank{self.rank_order} = {self.rank_value}"


class PolarMatchRule(models.Model):
    """Match-code rule table for Polar assessments (SRS §4.2.2).

    Per SRS §4.2.2: For polar assessments, the mapping value is NOT derived
    from band-number distance. Instead, the psychometrician defines a rule
    table mapping (criterion_band_code, user_band_code) -> (match_code, match_value):

      HM (High Match)         -> match_value 5
      MM (Moderate Match)     -> match_value 3
      LM (Low Match)          -> match_value 1

    The example in SRS §4.2.2 (Social-Reserved variable):
      Rule 1: criterion=SRC1, user=SRC1 -> HM, value 5  (perfect contrast1 match)
      Rule 2: criterion=SRM,  user=SRM  -> HM, value 5  (perfect middle match)
      Rule 3: criterion=SRC2, user=SRC2 -> HM, value 5  (perfect contrast2 match)
      Rules 4-7: moderate pairings -> MM, value 3
      Rules 8-9: low pairings -> LM, value 1

    This table is defined per BandDefinition (i.e., per variable within a
    polar selected_assessment).
    """

    MATCH_CODE_CHOICES = [
        ("HM", "High Match (value 5)"),
        ("MM", "Moderate Match (value 3)"),
        ("LM", "Low Match (value 1)"),
    ]

    band_definition = models.ForeignKey(
        BandDefinition,
        on_delete=models.CASCADE,
        related_name="polar_match_rules",
        help_text=_("The polar variable's band definition this rule applies to."),
    )
    criterion_band_code = models.CharField(
        _("criterion band code"), max_length=20, help_text=_("e.g., 'SRC1'")
    )
    user_band_code = models.CharField(
        _("user band code"), max_length=20, help_text=_("e.g., 'SRC1' or 'SRM'")
    )
    match_code = models.CharField(_("match code"), max_length=2, choices=MATCH_CODE_CHOICES)
    match_value = models.PositiveIntegerField(
        _("match value"),
        help_text=_("Numeric value: HM=5, MM=3, LM=1"),
        default=5,
    )

    class Meta:
        ordering = ["criterion_band_code", "user_band_code"]
        verbose_name = _("polar match rule")
        verbose_name_plural = _("polar match rules")
        unique_together = [
            ("band_definition", "criterion_band_code", "user_band_code"),
        ]

    def __str__(self) -> str:
        return (
            f"{self.criterion_band_code} vs {self.user_band_code} "
            f"-> {self.match_code} ({self.match_value})"
        )


class PolarRankValue(models.Model):
    """Rank value lookup for Polar assessments (SRS §4.2.3).

    Per SRS §4.2.3: the polar rank chart is 2-dimensional, indexed by
    (match_code, rank_order). Example:

        HM + Rank1 -> 7.0      MM + Rank1 -> 7.0      LM + Rank1 -> 3.0
        HM + Rank2 -> 6.4      MM + Rank2 -> 6.4      LM + Rank2 -> 3.6
        ...                   ...                   ...
        HM + Rank6 -> 2.0      MM + Rank6 -> 3.0      LM + Rank6 -> 7.0

    Note that for LM, the rank_value INCREASES with rank_order (the lowest
    rank gets the lowest value for HM but the highest value for LM) — this
    captures the SRS's "polar opposite" semantic.
    """

    MATCH_CODE_CHOICES = PolarMatchRule.MATCH_CODE_CHOICES

    rank_definition = models.ForeignKey(
        RankDefinition, on_delete=models.CASCADE, related_name="polar_rank_values"
    )
    match_code = models.CharField(_("match code"), max_length=2, choices=MATCH_CODE_CHOICES)
    rank_order = models.PositiveIntegerField(_("rank order"))
    rank_value = models.FloatField(_("rank value"))

    class Meta:
        ordering = ["match_code", "rank_order"]
        verbose_name = _("polar rank value")
        verbose_name_plural = _("polar rank values")
        unique_together = [("rank_definition", "match_code", "rank_order")]

    def __str__(self) -> str:
        return f"{self.match_code} + Rank{self.rank_order} = {self.rank_value}"


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
    # Career metadata — denormalised from MappingCriterion at compute time so
    # reports can group by stream without joining back to the criterion table.
    career_stream = models.CharField(_("career stream"), max_length=255, blank=True, default="")
    career_title = models.CharField(_("career title"), max_length=255)
    career_code = models.CharField(_("career code"), max_length=50, blank=True, default="")

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
        # A candidate has one MatchIndex per career per solution. career_code
        # is included to allow the same career_title under different streams
        # without colliding (though the SRS treats career_title as unique
        # within a solution).
        unique_together = [("solution", "candidate", "career_title", "career_code")]

    def __str__(self) -> str:
        return (
            f"{self.candidate.email} - {self.career_title} "
            f"(FMI: {self.final_match_index or '?'})"
        )
