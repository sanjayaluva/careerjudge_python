"""Serializers for the Reporting module."""

from rest_framework import serializers

from .models import (
    GeneratedReport,
    PolarVariable,
    Report,
    ReportBand,
    ReportCutoff,
    ReportSection,
    TypologicalCode,
)


class ReportSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSection
        fields = [
            "id",
            "report",
            "section_type",
            "title",
            "content",
            "table_graph_config",
            "order",
            "is_visible",
        ]
        read_only_fields = ["id"]


class ReportCutoffSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = ReportCutoff
        fields = [
            "id",
            "report",
            "section",
            "section_title",
            "cutoff_score",
            "cutoff_label",
            "above_description",
            "below_description",
        ]
        read_only_fields = ["id", "section_title"]


class ReportBandSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = ReportBand
        fields = [
            "id",
            "report",
            "section",
            "section_title",
            "band_number",
            "range_min",
            "range_max",
            "band_label",
            "description",
            "colour_code",
        ]
        read_only_fields = ["id", "section_title"]


class TypologicalCodeSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = TypologicalCode
        fields = ["id", "report", "section", "section_title", "code", "top_n"]
        read_only_fields = ["id", "section_title"]


class PolarVariableSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = PolarVariable
        fields = ["id", "report", "section", "section_title", "opposite_name"]
        read_only_fields = ["id", "section_title"]


class ReportSerializer(serializers.ModelSerializer):
    sections = ReportSectionSerializer(many=True, read_only=True)
    cutoffs = ReportCutoffSerializer(many=True, read_only=True)
    bands = ReportBandSerializer(many=True, read_only=True)
    typological_codes = TypologicalCodeSerializer(many=True, read_only=True)
    polar_variables = PolarVariableSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    assessment_title = serializers.CharField(
        source="assessment.title", read_only=True, default=None
    )
    profiling_solution_title = serializers.CharField(
        source="profiling_solution.title", read_only=True, default=None
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "objective",
            "description",
            "report_type",
            "scope",
            "status",
            "assessment",
            "assessment_title",
            "profiling_solution",
            "profiling_solution_title",
            "data_input_level",
            "stat_conversion",
            "include_score_summary",
            "include_section_breakdown",
            "include_question_analysis",
            "include_charts",
            "include_recommendations",
            "include_raw_summary",
            "include_fmi",
            "include_pmi",
            "include_vmi",
            "header_text",
            "footer_text",
            "logo",
            "created_by",
            "created_by_name",
            "sections",
            "cutoffs",
            "bands",
            "typological_codes",
            "polar_variables",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "sections",
            "cutoffs",
            "bands",
            "typological_codes",
            "polar_variables",
        ]


class ReportListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    assessment_title = serializers.CharField(
        source="assessment.title", read_only=True, default=None
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "objective",
            "report_type",
            "scope",
            "status",
            "assessment",
            "assessment_title",
            "data_input_level",
            "stat_conversion",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class GeneratedReportSerializer(serializers.ModelSerializer):
    report_title = serializers.CharField(source="report.title", read_only=True)
    candidate_name = serializers.CharField(
        source="candidate.full_name", read_only=True, default=None
    )
    assessment_title = serializers.CharField(
        source="session.assessment.title", read_only=True, default=None
    )

    class Meta:
        model = GeneratedReport
        fields = [
            "id",
            "report",
            "report_title",
            "session",
            "candidate",
            "candidate_name",
            "assessment_title",
            "rendered_data",
            "status",
            "error_message",
            "generated_at",
        ]
        read_only_fields = [
            "id",
            "candidate",
            "rendered_data",
            "status",
            "error_message",
            "generated_at",
            "report_title",
            "candidate_name",
            "assessment_title",
        ]
