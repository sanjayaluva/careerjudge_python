"""Serializers for the Career Profiling module."""

from rest_framework import serializers

from apps.assessment.serializers import AssessmentListSerializer

from .models import (
    Band,
    BandDefinition,
    MappingCriterion,
    MatchIndex,
    ProfilingSolution,
    SelectedAssessment,
)


class BandSerializer(serializers.ModelSerializer):
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


class SelectedAssessmentSerializer(serializers.ModelSerializer):
    assessment_detail = AssessmentListSerializer(source="assessment", read_only=True)
    band_definitions = BandDefinitionSerializer(many=True, read_only=True)

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
        ]
        read_only_fields = ["id", "assessment_detail", "band_definitions"]


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
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = MappingCriterion
        fields = [
            "id",
            "solution",
            "career_title",
            "section",
            "section_title",
            "criterion_band_code",
            "weight",
        ]
        read_only_fields = ["id", "section_title"]


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
            "career_title",
            "variable_mapping_index",
            "final_match_index",
            "variable_details",
            "computed_at",
        ]
        read_only_fields = [
            "id",
            "candidate",
            "variable_mapping_index",
            "final_match_index",
            "variable_details",
            "computed_at",
            "candidate_name",
        ]
