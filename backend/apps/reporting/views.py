"""Views for the Reporting module.

Endpoints:
  GET/POST  /api/reporting/reports/                    — list/create reports
  GET/PATCH /api/reporting/reports/<id>/                — retrieve/update
  DELETE    /api/reporting/reports/<id>/                — delete
  POST      /api/reporting/reports/<id>/publish/        — publish report
  POST      /api/reporting/reports/<id>/generate/       — generate report for a session
  GET       /api/reporting/reports/<id>/generated/      — list generated reports
  GET/POST  /api/reporting/reports/<id>/cutoffs/        — list/add cutoffs (descriptive)
  GET/POST  /api/reporting/reports/<id>/bands/          — list/add bands (interpretative)
  GET/POST  /api/reporting/reports/<id>/codes/          — list/add typological codes
  GET/POST  /api/reporting/reports/<id>/polar/          — list/add polar variables
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

from .generation import generate_report_data
from .models import (
    GeneratedReport,
    Report,
)
from .serializers import (
    GeneratedReportSerializer,
    PolarVariableSerializer,
    ReportBandSerializer,
    ReportCutoffSerializer,
    ReportListSerializer,
    ReportSerializer,
    TypologicalCodeSerializer,
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
        "cutoffs": "change",
        "bands": "change",
        "codes": "change",
        "polar": "change",
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
            {"message": "Report created.", "data": ReportSerializer(serializer.instance).data},
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
        # Validate scope: general reports need an assessment, profiling need a solution
        if report.scope == "general" and not report.assessment:
            return Response(
                {
                    "error": {
                        "code": "not_ready",
                        "message": "General reports must be linked to an assessment.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if report.scope == "profiling" and not report.profiling_solution:
            return Response(
                {
                    "error": {
                        "code": "not_ready",
                        "message": "Profiling reports must be linked to a profiling solution.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
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

        For general reports: uses the session's scores + report config (cutoffs,
        bands, typological codes, polar variables).
        For profiling reports: uses the profiling solution's match indices.
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
        session = get_object_or_404(AssessmentSession, id=session_id)

        # Scope validation: general reports require the session's assessment
        # to match the report's linked assessment
        if (
            report.scope == "general"
            and report.assessment
            and session.assessment_id != report.assessment_id
        ):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Session's assessment does not match this report's assessment.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if session.status != "completed":
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Session must be completed to generate a report.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        # Generate the rendered data using the generation engine
        try:
            rendered_data = generate_report_data(report, session)
        except Exception as e:
            gen_report = GeneratedReport.objects.create(
                report=report,
                session=session,
                candidate=session.candidate,
                status="failed",
                error_message=str(e),
            )
            return Response(
                {"error": {"code": "generation_failed", "message": str(e)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        gen_report = GeneratedReport.objects.create(
            report=report,
            session=session,
            candidate=session.candidate,
            rendered_data=rendered_data,
            status="generated",
        )
        return Response(
            {"message": "Report generated.", "data": GeneratedReportSerializer(gen_report).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def generated(self, request, pk=None):
        """List all generated reports for this report definition."""
        report = self.get_object()
        gen_reports = report.generated_reports.select_related("candidate", "session").all()
        serializer = GeneratedReportSerializer(gen_reports, many=True)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    # --- Nested config endpoints ---

    @action(detail=True, methods=["get", "post"])
    def cutoffs(self, request, pk=None):
        """List or add cutoffs (descriptive reports)."""
        report = self.get_object()
        if request.method == "GET":
            cutoffs = report.cutoffs.select_related("section").all()
            return Response(
                {"message": "OK", "data": ReportCutoffSerializer(cutoffs, many=True).data},
                status=status.HTTP_200_OK,
            )
        serializer = ReportCutoffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(report=report)
        return Response(
            {"message": "Cutoff created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def bands(self, request, pk=None):
        """List or add bands (interpretative reports)."""
        report = self.get_object()
        if request.method == "GET":
            bands = report.bands.select_related("section").all()
            return Response(
                {"message": "OK", "data": ReportBandSerializer(bands, many=True).data},
                status=status.HTTP_200_OK,
            )
        serializer = ReportBandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(report=report)
        return Response(
            {"message": "Band created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def codes(self, request, pk=None):
        """List or add typological codes (typological reports)."""
        report = self.get_object()
        if request.method == "GET":
            codes = report.typological_codes.select_related("section").all()
            return Response(
                {"message": "OK", "data": TypologicalCodeSerializer(codes, many=True).data},
                status=status.HTTP_200_OK,
            )
        serializer = TypologicalCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(report=report)
        return Response(
            {"message": "Code created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def polar(self, request, pk=None):
        """List or add polar variables."""
        report = self.get_object()
        if request.method == "GET":
            polar = report.polar_variables.select_related("section").all()
            return Response(
                {"message": "OK", "data": PolarVariableSerializer(polar, many=True).data},
                status=status.HTTP_200_OK,
            )
        serializer = PolarVariableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(report=report)
        return Response(
            {"message": "Polar variable created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


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
