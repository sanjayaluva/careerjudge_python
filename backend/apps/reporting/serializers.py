"""Serializers for the Reporting module."""

from rest_framework import serializers

from .models import GeneratedReport, Report, ReportSection


class ReportSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSection
        fields = [
            "id",
            "report",
            "section_type",
            "title",
            "content",
            "order",
            "is_visible",
        ]
        read_only_fields = ["id"]


class ReportSerializer(serializers.ModelSerializer):
    sections = ReportSectionSerializer(many=True, read_only=True)
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
            "include_score_summary",
            "include_section_breakdown",
            "include_question_analysis",
            "include_charts",
            "include_recommendations",
            "header_text",
            "footer_text",
            "logo",
            "created_by",
            "created_by_name",
            "sections",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "sections"]


class ReportListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

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
