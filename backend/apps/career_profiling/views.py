"""Views for the Career Profiling module.

Endpoints:
  GET/POST  /api/career-profiling/solutions/                — list/create solutions
  GET/PATCH /api/career-profiling/solutions/<id>/            — retrieve/update
  DELETE    /api/career-profiling/solutions/<id>/            — delete
  POST      /api/career-profiling/solutions/<id>/publish/    — publish solution
  GET/POST  /api/career-profiling/solutions/<id>/assessments/ — list/add assessments
  GET/POST  /api/career-profiling/solutions/<id>/bands/      — list/add band definitions
  GET/POST  /api/career-profiling/solutions/<id>/criteria/   — list/add mapping criteria
  GET       /api/career-profiling/solutions/<id>/match-indices/ — list match indices
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions import HasModulePermission

from .models import (
    BandDefinition,
    ProfilingSolution,
)
from .serializers import (
    BandDefinitionSerializer,
    MappingCriterionSerializer,
    MatchIndexSerializer,
    PolarMatchRuleSerializer,
    ProfilingSolutionListSerializer,
    ProfilingSolutionSerializer,
    RankDefinitionSerializer,
    SelectedAssessmentSerializer,
)


class HasProfilingPermission(HasModulePermission):
    module = "career_profiling"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
        "publish": "change",
        "compute": "view",  # any user with view permission may compute (admins for any candidate, others for self)
        "rank_definitions": "change",
        "rank_definitions_delete": "change",
        "polar_match_rules": "change",
    }


class ProfilingSolutionViewSet(ModelViewSet):
    """CRUD for profiling solutions."""

    queryset = ProfilingSolution.objects.select_related("created_by").prefetch_related(
        "selected_assessments"
    )
    permission_classes = [IsAuthenticated, HasProfilingPermission]
    serializer_class = ProfilingSolutionSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return ProfilingSolutionListSerializer
        return ProfilingSolutionSerializer

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
                "message": "Profiling solution created.",
                "data": ProfilingSolutionSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a profiling solution."""
        solution = self.get_object()
        if solution.status != "draft":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Solution must be in 'draft' status. Current: '{solution.status}'",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        # Validate: at least 2 assessments selected
        if solution.selected_assessments.count() < 2:
            return Response(
                {
                    "error": {
                        "code": "not_ready",
                        "message": "At least 2 assessments must be selected before publishing.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        solution.status = "published"
        solution.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "message": "Solution published.",
                "data": {"id": solution.id, "status": solution.status},
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"])
    def assessments(self, request, pk=None):
        """List or add assessments to a solution."""
        solution = self.get_object()
        if request.method == "GET":
            assessments = solution.selected_assessments.all()
            serializer = SelectedAssessmentSerializer(assessments, many=True)
            return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            # POST: add an assessment
            serializer = SelectedAssessmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # Validate max 3 assessments
            if solution.selected_assessments.count() >= 3:
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": "Maximum 3 assessments per solution.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.save(solution=solution)
            return Response(
                {"message": "Assessment added.", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

    @action(detail=True, methods=["get", "post"])
    def bands(self, request, pk=None):
        """List or add band definitions for a solution's assessments."""
        solution = self.get_object()
        if request.method == "GET":
            band_defs = BandDefinition.objects.filter(
                selected_assessment__solution=solution
            ).select_related("section", "selected_assessment")
            serializer = BandDefinitionSerializer(band_defs, many=True)
            return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            serializer = BandDefinitionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"message": "Band definition created.", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

    @action(detail=True, methods=["get", "post"])
    def rank_definitions(self, request, pk=None):
        """List or create RankDefinitions (SRS §4.1.3 + §4.2.3) for the
        solution's selected_assessments.

        GET /solutions/<id>/rank_definitions/
          -> list of all rank definitions in the solution (with nested
             rank_values for standard mode or polar_rank_values for polar mode)

        POST /solutions/<id>/rank_definitions/
          body: {
            "selected_assessment": 42,
            "is_polar": false,
            "rank_values": [
              {"rank_order": 1, "rank_value": 2.0},
              {"rank_order": 2, "rank_value": 1.8},
              ...
            ]
            // OR for polar:
            // "polar_rank_values": [
            //   {"match_code": "HM", "rank_order": 1, "rank_value": 7.0},
            //   {"match_code": "MM", "rank_order": 1, "rank_value": 7.0},
            //   {"match_code": "LM", "rank_order": 1, "rank_value": 3.0},
            //   ...
            // ]
          }
        """
        solution = self.get_object()
        if request.method == "GET":
            from .models import RankDefinition

            rank_defs = RankDefinition.objects.filter(
                selected_assessment__solution=solution
            ).select_related("selected_assessment")
            serializer = RankDefinitionSerializer(rank_defs, many=True)
            return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

        # POST: create a rank definition with nested values
        from .models import PolarRankValue, RankDefinition, RankValue

        sa_id = request.data.get("selected_assessment")
        is_polar = bool(request.data.get("is_polar", False))
        # Validate the selected_assessment belongs to this solution
        sa = solution.selected_assessments.filter(id=sa_id).first()
        if not sa:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": (f"selected_assessment {sa_id} not found in this solution."),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Reject if a rank definition already exists for this assessment
        if hasattr(sa, "rank_definition"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": (
                            f"Selected assessment '{sa.label}' already has a rank definition. "
                            "Delete it first to replace."
                        ),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        rank_values_data = request.data.get("rank_values") or []
        polar_rank_values_data = request.data.get("polar_rank_values") or []
        if not is_polar and not rank_values_data:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "rank_values (non-empty list) is required for standard mode.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if is_polar and not polar_rank_values_data:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": (
                            "polar_rank_values (non-empty list) is required for polar mode."
                        ),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        rd = RankDefinition.objects.create(selected_assessment=sa, is_polar=is_polar)
        if not is_polar:
            for rv in rank_values_data:
                RankValue.objects.create(
                    rank_definition=rd,
                    rank_order=rv["rank_order"],
                    rank_value=rv["rank_value"],
                )
        else:
            for pv in polar_rank_values_data:
                PolarRankValue.objects.create(
                    rank_definition=rd,
                    match_code=pv["match_code"],
                    rank_order=pv["rank_order"],
                    rank_value=pv["rank_value"],
                )

        serializer = RankDefinitionSerializer(rd)
        return Response(
            {"message": "Rank definition created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete"])
    def rank_definitions_delete(self, request, pk=None):
        """Delete a RankDefinition by ID (cascades to its rank values).

        DELETE /solutions/<id>/rank_definitions_delete/?rd_id=42
        """
        from .models import RankDefinition

        solution = self.get_object()
        rd_id = request.query_params.get("rd_id")
        if not rd_id:
            return Response(
                {"error": {"code": "validation_error", "message": "rd_id query param required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rd = RankDefinition.objects.filter(id=rd_id, selected_assessment__solution=solution).first()
        if not rd:
            return Response(
                {"error": {"code": "not_found", "message": "Rank definition not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        rd.delete()
        return Response(
            {"message": "Rank definition deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"])
    def polar_match_rules(self, request, pk=None):
        """List or create PolarMatchRules (SRS §4.2.2) for the solution's
        band_definitions.

        GET /solutions/<id>/polar_match_rules/
          -> list of all polar match rules in the solution

        POST /solutions/<id>/polar_match_rules/
          body: {
            "band_definition": 42,
            "criterion_band_code": "SRC1",
            "user_band_code": "SRC1",
            "match_code": "HM",
            "match_value": 5
          }
        """
        solution = self.get_object()
        if request.method == "GET":
            from .models import PolarMatchRule

            rules = PolarMatchRule.objects.filter(
                band_definition__selected_assessment__solution=solution
            ).select_related("band_definition")
            serializer = PolarMatchRuleSerializer(rules, many=True)
            return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

        from .models import BandDefinition, PolarMatchRule

        bd_id = request.data.get("band_definition")
        bd = BandDefinition.objects.filter(id=bd_id, selected_assessment__solution=solution).first()
        if not bd:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": f"band_definition {bd_id} not found in this solution.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PolarMatchRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Polar match rule created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def criteria(self, request, pk=None):
        """List or add mapping criteria for a solution."""
        solution = self.get_object()
        if request.method == "GET":
            criteria = solution.mapping_criteria.select_related("section").all()
            serializer = MappingCriterionSerializer(criteria, many=True)
            return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            serializer = MappingCriterionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(solution=solution)
            return Response(
                {"message": "Mapping criterion created.", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

    @action(detail=True, methods=["get"])
    def match_indices(self, request, pk=None):
        """List match indices computed for this solution."""
        solution = self.get_object()
        indices = solution.match_indices.select_related("candidate").all()
        serializer = MatchIndexSerializer(indices, many=True)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def compute(self, request, pk=None):
        """Compute MatchIndex records for a candidate against every career in
        this solution.

        Triggers the SRS §5.1-5.3 algorithm:
          mapping_score → VMI → PMI → FMI

        Permissions:
          - cj_admin / psychometrician: may pass `candidate_id` in the body to
            compute for any user. Otherwise computes for the authenticated user.
          - Other roles: may only compute for themselves (candidate_id is
            ignored and the authenticated user is used).

        Returns the list of created/updated MatchIndex records. Records are
        skipped (and omitted from the response) when the candidate has no
        completed session for any of the solution's assessments, or when a
        career has no scorable variables.

        POST /api/career-profiling/solutions/<id>/compute/
          body: {"candidate_id": 42}   # optional for admins
        """
        from .engine import compute_match_indices

        solution = self.get_object()
        if solution.status != "published":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": (
                            f"Solution must be 'published' before computing match "
                            f"indices. Current status: '{solution.status}'."
                        ),
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Determine target candidate
        user_role_name = request.user.role.name if request.user.role_id else None
        is_admin = user_role_name in ("cj_admin", "psychometrician")
        candidate_id = request.data.get("candidate_id")
        if candidate_id and is_admin:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            from django.shortcuts import get_object_or_404 as _get_obj_or_404

            candidate = _get_obj_or_404(User, pk=candidate_id)
        else:
            candidate = request.user

        match_indices = compute_match_indices(solution, candidate)
        serializer = MatchIndexSerializer(match_indices, many=True)
        return Response(
            {
                "message": f"Computed {len(match_indices)} match index record(s).",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
