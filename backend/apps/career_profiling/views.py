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
    ProfilingSolutionListSerializer,
    ProfilingSolutionSerializer,
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
