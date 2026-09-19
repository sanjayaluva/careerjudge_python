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
            "description",
            "image",
            "table_graph_config",
            "order",
            "is_visible",
        ]
        # `report` is set by the view (POST /reports/<id>/sections/ passes
        # `report=report` to serializer.save()), not by the client — making
        # it read-only here matches how the `sections` create endpoint (and
        # the frontend's createSection(), which never sends `report`) is
        # actually used.
        read_only_fields = ["id", "report"]


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
        # `report` is set by the view (POST /reports/<id>/cutoffs/ passes
        # report=report to save()); the config endpoints never receive it in
        # the body, so it must be read-only or is_valid() rejects it as
        # required before the view can inject it.
        read_only_fields = ["id", "report", "section_title"]


class ReportBandSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = ReportBand
        fields = [
            "id",
            "report",
            "target_type",
            "section",
            "section_title",
            "assessment_label",
            "band_number",
            "range_min",
            "range_max",
            "band_label",
            "description",
            "colour_code",
        ]
        # `report` is injected by the view via save(report=report); keep it
        # read-only so is_valid() does not demand it in the request body.
        read_only_fields = ["id", "report", "section_title"]
        extra_kwargs = {
            # section is only required for target_type='section'; profiling
            # bands (fmi/pmi/vmi/raw_summary/pmi_d) leave it blank.
            "section": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        target = attrs.get("target_type", getattr(self.instance, "target_type", "section"))
        section = attrs.get("section", getattr(self.instance, "section", None))
        if target == "section" and section is None:
            raise serializers.ValidationError(
                {"section": "section is required when target_type='section'."}
            )
        return attrs


class TypologicalCodeSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = TypologicalCode
        fields = ["id", "report", "section", "section_title", "code", "top_n"]
        # `report` is injected by the view via save(report=report).
        read_only_fields = ["id", "report", "section_title"]


class PolarVariableSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)

    class Meta:
        model = PolarVariable
        fields = ["id", "report", "section", "section_title", "opposite_name"]
        # `report` is injected by the view via save(report=report).
        read_only_fields = ["id", "report", "section_title"]


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
            "pmi_d_first_assessment",
            "pmi_d_second_assessment",
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
