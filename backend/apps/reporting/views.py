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

from .generation import generate_group_report_data, generate_report_data, select_profiling_data
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
        "generate_group": "view",
        "select_data": "view",
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

    @action(detail=True, methods=["post"])
    def generate_group(self, request, pk=None):
        """Generate a group report aggregating multiple completed sessions.

        Per SRS 04 group report: corporate managers view their employees'
        performance on the assessment.

        Payload:
            {"session_ids": [1, 2, 3, ...]}

        Returns the aggregated group data (candidate_count, average_score,
        average_percentage, pass_rate, section_averages, distribution,
        candidates list). Does NOT persist a GeneratedReport row (group
        reports span multiple sessions, so they're computed on demand).
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
        if report.report_type != "group":
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": (
                            f"generate_group is only for group reports. "
                            f"This report's type is '{report.report_type}'."
                        ),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_ids = request.data.get("session_ids") or []
        if not session_ids or not isinstance(session_ids, list):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "session_ids (list of ints) is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.assessment.models import AssessmentSession

        sessions = list(
            AssessmentSession.objects.filter(id__in=session_ids, status="completed")
            .select_related("candidate", "assessment")
            .prefetch_related("section_scores__section")
        )
        # Validate every requested session was found and completed
        found_ids = {s.id for s in sessions}
        missing = set(session_ids) - found_ids
        if missing:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": (
                            f"These session IDs were not found or not completed: "
                            f"{sorted(missing)}"
                        ),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # All sessions should belong to the same assessment as the report
        if report.assessment_id:
            wrong = [s for s in sessions if s.assessment_id != report.assessment_id]
            if wrong:
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": (
                                f"Sessions {[s.id for s in wrong]} belong to a different "
                                f"assessment than the report."
                            ),
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        rendered_data = generate_group_report_data(report, sessions)
        return Response(
            {"message": "Group report generated.", "data": rendered_data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def select_data(self, request, pk=None):
        """HFMI / LFMI data selection for profiling reports (SRS 06 SRS 2.2).

        Payload:
            {
                "candidate_id": 42,                    # required
                "data_type": "HFMI" | "LFMI",          # required
                "extraction_mode": "user" | "system",  # required
                "fmi_range": [85, 100],                # user mode only
                "n_categories": 3,                     # system mode only
                "n_criterions": 5,                     # system mode only
                "selected_career_titles": ["..."]      # user mode, optional
            }

        Returns the filtered/sorted MatchIndex list. For user-initiated
        selection without selected_career_titles, returns the filtered list
        so the UI can present it for the user to choose from.
        """
        report = self.get_object()
        if report.scope != "profiling" or not report.profiling_solution:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "select_data is only for profiling reports.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        candidate_id = request.data.get("candidate_id")
        data_type = request.data.get("data_type", "HFMI")
        extraction_mode = request.data.get("extraction_mode", "system")
        fmi_range = request.data.get("fmi_range")
        n_categories = int(request.data.get("n_categories", 0))
        n_criterions = int(request.data.get("n_criterions", 0))
        selected_career_titles = request.data.get("selected_career_titles")

        if not candidate_id:
            return Response(
                {"error": {"code": "validation_error", "message": "candidate_id is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if data_type not in ("HFMI", "LFMI"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "data_type must be 'HFMI' or 'LFMI'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if extraction_mode not in ("user", "system"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "extraction_mode must be 'user' or 'system'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.career_profiling.models import MatchIndex

        match_indices = list(
            MatchIndex.objects.filter(
                solution=report.profiling_solution,
                candidate_id=candidate_id,
            ).exclude(final_match_index__isnull=True)
        )

        fmi_range_tuple = tuple(fmi_range) if fmi_range and len(fmi_range) == 2 else None
        result = select_profiling_data(
            match_indices,
            data_type=data_type,
            extraction_mode=extraction_mode,
            fmi_range=fmi_range_tuple,
            n_categories=n_categories,
            n_criterions=n_criterions,
            selected_career_titles=selected_career_titles,
        )
        return Response({"message": "OK", "data": result}, status=status.HTTP_200_OK)

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
