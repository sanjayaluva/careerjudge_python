"""Serializers for the Career Profiling module."""

from rest_framework import serializers

from apps.assessment.serializers import AssessmentListSerializer

from .models import (
    Band,
    BandDefinition,
    MappingCriterion,
    MappingRule,
    MatchIndex,
    PolarMatchRule,
    PolarRankValue,
    ProfilingSolution,
    RankDefinition,
    RankValue,
    SelectedAssessment,
)


class BandSerializer(serializers.ModelSerializer):
    """Band row within a BandDefinition.

    Per SRS §4.1.1 "Band Definition" rules, enforced here at row-creation
    time (per-row rules only — "min 2 bands per variable" and "min 2
    variables selected" cannot be checked one row at a time and are instead
    enforced when the solution is published; see
    ProfilingSolutionViewSet.publish):
      - Band range must be within 0-100 (inclusive), range_min < range_max
      - Max 10 bands per variable (band_definition)
      - Two bands must not overlap
    """

    MAX_BANDS_PER_DEFINITION = 10

    class Meta:
        model = Band
        fields = [
            "id",
            "band_definition",
            "band_number",
            "range_min",
            "range_max",
            "band_code",
            "sub_variable_name",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        band_definition = attrs.get("band_definition") or getattr(
            self.instance, "band_definition", None
        )
        range_min = attrs.get("range_min", getattr(self.instance, "range_min", 0))
        range_max = attrs.get("range_max", getattr(self.instance, "range_max", 100))

        if range_min < 0 or range_max > 100:
            raise serializers.ValidationError(
                "Band range must be between 0 and 100 (inclusive)."
            )
        if range_min >= range_max:
            raise serializers.ValidationError("range_min must be less than range_max.")

        if band_definition is not None:
            existing = Band.objects.filter(band_definition=band_definition)
            if self.instance is not None:
                existing = existing.exclude(pk=self.instance.pk)

            if self.instance is None and existing.count() >= self.MAX_BANDS_PER_DEFINITION:
                raise serializers.ValidationError(
                    f"Maximum {self.MAX_BANDS_PER_DEFINITION} bands per variable "
                    f"(band_definition {band_definition.id} already has "
                    f"{existing.count()})."
                )

            for other in existing:
                # Inclusive ranges overlap unless one ends strictly before
                # the other begins.
                if range_min <= other.range_max and range_max >= other.range_min:
                    raise serializers.ValidationError(
                        f"Band range [{range_min}, {range_max}] overlaps existing "
                        f"band '{other.band_code}' [{other.range_min}, {other.range_max}]."
                    )

        return attrs


class BandDefinitionSerializer(serializers.ModelSerializer):
    bands = BandSerializer(many=True, read_only=True)
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = BandDefinition
        fields = [
            "id",
            "selected_assessment",
            "section",
            "section_title",
            "bands",
        ]
        read_only_fields = ["id", "bands", "section_title"]


class RankValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = RankValue
        fields = ["id", "rank_definition", "rank_order", "rank_value"]
        read_only_fields = ["id"]


class PolarRankValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolarRankValue
        fields = ["id", "rank_definition", "match_code", "rank_order", "rank_value"]
        read_only_fields = ["id"]


class RankDefinitionSerializer(serializers.ModelSerializer):
    rank_values = RankValueSerializer(many=True, read_only=True)
    polar_rank_values = PolarRankValueSerializer(many=True, read_only=True)

    class Meta:
        model = RankDefinition
        fields = [
            "id",
            "selected_assessment",
            "is_polar",
            "rank_values",
            "polar_rank_values",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "rank_values", "polar_rank_values"]


class PolarMatchRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolarMatchRule
        fields = [
            "id",
            "band_definition",
            "criterion_band_code",
            "user_band_code",
            "match_code",
            "match_value",
        ]
        read_only_fields = ["id"]


class MappingRuleSerializer(serializers.ModelSerializer):
    """Writable serializer for the standard mapping-rule table (SRS §4.1.2)."""

    class Meta:
        model = MappingRule
        fields = [
            "id",
            "band_definition",
            "criterion_band_code",
            "user_band_code",
            "value",
        ]
        read_only_fields = ["id"]


class SelectedAssessmentSerializer(serializers.ModelSerializer):
    assessment_detail = AssessmentListSerializer(source="assessment", read_only=True)
    band_definitions = BandDefinitionSerializer(many=True, read_only=True)
    rank_definition = RankDefinitionSerializer(read_only=True)

    class Meta:
        model = SelectedAssessment
        fields = [
            "id",
            "solution",
            "assessment",
            "assessment_detail",
            "label",
            "is_polar",
            "order",
            "band_definitions",
            "rank_definition",
        ]
        read_only_fields = ["id", "assessment_detail", "band_definitions", "rank_definition"]


class ProfilingSolutionSerializer(serializers.ModelSerializer):
    selected_assessments = SelectedAssessmentSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    assessment_count = serializers.IntegerField(source="selected_assessments.count", read_only=True)

    class Meta:
        model = ProfilingSolution
        fields = [
            "id",
            "title",
            "purpose",
            "description",
            "image",
            "status",
            "has_polar_assessment",
            "created_by",
            "created_by_name",
            "assessment_count",
            "selected_assessments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "selected_assessments"]


class ProfilingSolutionListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    assessment_count = serializers.IntegerField(source="selected_assessments.count", read_only=True)

    class Meta:
        model = ProfilingSolution
        fields = [
            "id",
            "title",
            "purpose",
            "status",
            "has_polar_assessment",
            "created_by",
            "created_by_name",
            "assessment_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class MappingCriterionSerializer(serializers.ModelSerializer):
    """Criterion definition for one career x variable.

    Per D5 gap: criterion_band_code is validated as a choice constrained to
    the band codes actually defined (Band rows) for the given section within
    the solution passed in context["solution"] — rather than free text.
    When no `solution` is in context (e.g. serializing for read), the choice
    check is skipped.
    """

    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = MappingCriterion
        fields = [
            "id",
            "solution",
            "career_stream",
            "career_title",
            "career_code",
            "career_description",
            "section",
            "section_title",
            "criterion_band_code",
            "rank_order",
            "weight",
        ]
        # "solution" is assigned by the view (serializer.save(solution=solution)),
        # never supplied by the client — mirrors how Question.created_by /
        # Category.created_by are handled elsewhere. Without this, the model's
        # required FK made the field mandatory in the request body too, which
        # the "criteria" POST endpoint never sent (pre-existing gap — this
        # endpoint had no API-level test coverage before D5 item 6/7).
        read_only_fields = ["id", "section_title", "solution"]

    def validate(self, attrs):
        solution = self.context.get("solution") or getattr(self.instance, "solution", None)
        section = attrs.get("section") or getattr(self.instance, "section", None)
        band_code = attrs.get("criterion_band_code")

        if solution is not None and section is not None and band_code:
            valid_codes = list(
                Band.objects.filter(
                    band_definition__selected_assessment__solution=solution,
                    band_definition__section=section,
                ).values_list("band_code", flat=True)
            )
            if not valid_codes:
                raise serializers.ValidationError(
                    {
                        "criterion_band_code": (
                            f"No bands are defined for variable '{section.title}' in this "
                            "solution yet — define bands before setting a criterion."
                        )
                    }
                )
            if band_code not in valid_codes:
                raise serializers.ValidationError(
                    {
                        "criterion_band_code": (
                            f"'{band_code}' is not a defined band code for variable "
                            f"'{section.title}'. Valid codes: {sorted(valid_codes)}."
                        )
                    }
                )

        return attrs


class MatchIndexSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(
        source="candidate.full_name", read_only=True, default=None
    )

    class Meta:
        model = MatchIndex
        fields = [
            "id",
            "solution",
            "candidate",
            "candidate_name",
            "career_stream",
            "career_title",
            "career_code",
            "variable_mapping_index",
            "final_match_index",
            "variable_details",
            "computed_at",
        ]
        read_only_fields = [
            "id",
            "candidate",
            "career_stream",
            "variable_mapping_index",
            "final_match_index",
            "variable_details",
            "computed_at",
            "candidate_name",
        ]
