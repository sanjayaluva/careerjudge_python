"""Views for the Reporting module.

Endpoints:
  GET/POST  /api/reporting/reports/                    — list/create reports
  GET/PATCH /api/reporting/reports/<id>/                — retrieve/update
  DELETE    /api/reporting/reports/<id>/                — delete
  POST      /api/reporting/reports/<id>/publish/        — publish report
  POST      /api/reporting/reports/<id>/generate/       — generate report for a session
  GET       /api/reporting/reports/<id>/generated/      — list generated reports
  GET       /api/reporting/generated/<id>/              — retrieve a generated report
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.mixins import ActionSerializerMixin
from core.permissions import HasModulePermission

from .models import GeneratedReport, Report
from .serializers import (
    GeneratedReportSerializer,
    ReportListSerializer,
    ReportSerializer,
)


class HasReportingPermission(HasModulePermission):
    module = "reporting"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
        "publish": "change",
        "generate": "view",
    }


class ReportViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for reports."""

    queryset = Report.objects.select_related("created_by", "assessment", "profiling_solution")
    permission_classes = [IsAuthenticated, HasReportingPermission]
    serializer_class = ReportSerializer
    serializer_classes = {
        "list": ReportListSerializer,
    }

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Report created.",
                "data": ReportSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a report."""
        report = self.get_object()
        if report.status != "draft":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Report must be in 'draft' status. Current: '{report.status}'",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        report.status = "published"
        report.save(update_fields=["status", "updated_at"])
        return Response(
            {"message": "Report published.", "data": {"id": report.id, "status": report.status}},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """Generate a report for a completed assessment session.

        Payload: {session_id: int}
        """
        report = self.get_object()
        if report.status != "published":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Report must be published before generating.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        from apps.assessment.models import AssessmentSession

        session_id = request.data.get("session_id")
        session = get_object_or_404(AssessmentSession, id=session_id, status="completed")

        # Check if already generated
        existing = GeneratedReport.objects.filter(report=report, session=session).first()
        if existing:
            return Response(
                {
                    "message": "Report already generated for this session.",
                    "data": GeneratedReportSerializer(existing).data,
                },
                status=status.HTTP_200_OK,
            )

        # Build the rendered data
        rendered_data = {
            "report_title": report.title,
            "report_type": report.report_type,
            "assessment_title": session.assessment.title,
            "candidate": {
                "id": session.candidate.id,
                "name": session.candidate.full_name,
                "email": session.candidate.email,
            },
            "session": {
                "id": session.id,
                "started_at": session.started_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            },
            "scores": {
                "total_score": session.total_score,
                "max_score": session.max_score,
                "percentage": session.percentage,
            },
        }

        # Add section breakdown if enabled
        if report.include_section_breakdown:
            section_scores = []
            for ss in session.section_scores.select_related("section").all():
                section_scores.append(
                    {
                        "section_title": ss.section.title,
                        "level": ss.section.level,
                        "raw_score": ss.raw_score,
                        "max_score": ss.max_score,
                        "percentage": ss.percentage,
                    }
                )
            rendered_data["section_breakdown"] = section_scores

        # Add sections content (narratives, recommendations, etc.)
        sections = []
        for rs in report.sections.filter(is_visible=True).order_by("order"):
            sections.append(
                {
                    "type": rs.section_type,
                    "title": rs.title,
                    "content": rs.content,
                    "order": rs.order,
                }
            )
        rendered_data["sections"] = sections

        gen_report = GeneratedReport.objects.create(
            report=report,
            session=session,
            candidate=session.candidate,
            rendered_data=rendered_data,
            status="generated",
        )

        return Response(
            {
                "message": "Report generated.",
                "data": GeneratedReportSerializer(gen_report).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def generated(self, request, pk=None):
        """List all generated reports for this report definition."""
        report = self.get_object()
        gen_reports = report.generated_reports.select_related("candidate", "session").all()
        serializer = GeneratedReportSerializer(gen_reports, many=True)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)


class GeneratedReportViewSet(ModelViewSet):
    """Retrieve generated reports."""

    queryset = GeneratedReport.objects.select_related("report", "session", "candidate")
    permission_classes = [IsAuthenticated]
    serializer_class = GeneratedReportSerializer
    http_method_names = ["get", "head", "options"]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)
