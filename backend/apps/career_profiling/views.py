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
  GET/POST  /api/career-profiling/solutions/<id>/criteria-upload/ — download template /
                                                                      upload criteria CSV
"""

import csv
import io

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions import HasModulePermission

from .models import (
    BandDefinition,
    MappingCriterion,
    ProfilingSolution,
)
from .serializers import (
    BandDefinitionSerializer,
    BandSerializer,
    MappingCriterionSerializer,
    MappingRuleSerializer,
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
        "mapping_rules": "change",
        "band_rows": "change",
        "criteria_upload": "change",
        # "criteria" was missing from this map entirely (pre-existing gap —
        # every non-superuser got 403 on GET/POST .../criteria/, including
        # the psychometrician role). Added while wiring the band-dropdown
        # validation (D5 item 6) since that endpoint needs to be reachable.
        "criteria": "change",
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

        # Band definition guards (SRS §4.1.1 / §4.2.1) — checked once per
        # selected_assessment since "at least 2 bands per variable" can't be
        # enforced one Band row at a time (see BandSerializer for the
        # per-row range/overlap/max-10 checks).
        band_errors = []
        for sa in solution.selected_assessments.all():
            band_defs = list(sa.band_definitions.all())
            if len(band_defs) < 2:
                band_errors.append(
                    f"Assessment '{sa.label}': at least 2 variables must have bands "
                    f"defined (found {len(band_defs)})."
                )
            for bd in band_defs:
                n_bands = bd.bands.count()
                if n_bands < 2:
                    band_errors.append(
                        f"Assessment '{sa.label}' / variable '{bd.section.title}': "
                        f"at least 2 bands are required (found {n_bands})."
                    )
        if band_errors:
            return Response(
                {
                    "error": {
                        "code": "not_ready",
                        "message": "Band definitions are incomplete:\n• " + "\n• ".join(band_errors),
                        "details": {"errors": band_errors},
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
    def band_rows(self, request, pk=None):
        """List or create individual Band rows (SRS §4.1.1) nested under a
        band_definition belonging to this solution.

        GET /solutions/<id>/band_rows/
          -> list of all bands across the solution's band_definitions

        POST /solutions/<id>/band_rows/
          body: {
            "band_definition": 42,
            "band_number": 1,
            "range_min": 0,
            "range_max": 20,
            "band_code": "ANL2",
            "sub_variable_name": ""   // optional (polar)
          }
        """
        solution = self.get_object()
        if request.method == "GET":
            from .models import Band

            bands = Band.objects.filter(
                band_definition__selected_assessment__solution=solution
            ).select_related("band_definition")
            serializer = BandSerializer(bands, many=True)
            return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

        bd_id = request.data.get("band_definition")
        bd = BandDefinition.objects.filter(
            id=bd_id, selected_assessment__solution=solution
        ).first()
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

        serializer = BandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Band created.", "data": serializer.data},
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
    def mapping_rules(self, request, pk=None):
        """List or create MappingRules (SRS §4.1.2) for the solution's
        standard band_definitions.

        GET /solutions/<id>/mapping_rules/
          -> list of all mapping rules in the solution

        POST /solutions/<id>/mapping_rules/
          body: {
            "band_definition": 42,
            "criterion_band_code": "ANH2",
            "user_band_code": "ANH1",
            "value": 4
          }
        """
        solution = self.get_object()
        if request.method == "GET":
            from .models import MappingRule

            rules = MappingRule.objects.filter(
                band_definition__selected_assessment__solution=solution
            ).select_related("band_definition")
            serializer = MappingRuleSerializer(rules, many=True)
            return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

        bd_id = request.data.get("band_definition")
        bd = BandDefinition.objects.filter(
            id=bd_id, selected_assessment__solution=solution
        ).first()
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

        serializer = MappingRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Mapping rule created.", "data": serializer.data},
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
            serializer = MappingCriterionSerializer(
                data=request.data, context={"solution": solution}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(solution=solution)
            return Response(
                {"message": "Mapping criterion created.", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

    def _solution_band_definitions(self, solution):
        """Ordered BandDefinitions across all of the solution's selected
        assessments, with their valid band codes preloaded."""
        return list(
            BandDefinition.objects.filter(selected_assessment__solution=solution)
            .select_related("section", "selected_assessment")
            .order_by("selected_assessment__order", "section__level", "section__order")
        )

    @action(detail=True, methods=["get", "post"], url_path="criteria-upload")
    def criteria_upload(self, request, pk=None):
        """Criterion definition via template upload (SRS §4.1.4).

        GET  -> downloads a CSV template with one Band Code / Rank Order
                column pair per variable currently banded in this solution.
        POST -> uploads a filled-in CSV and creates/updates MappingCriterion
                rows (one per career x variable). Existing criteria for the
                same (career_stream, career_title, section) are updated
                (idempotent re-upload).

        Column format (SRS §4.1.4 criterion_data_upload_format):
          Career Stream, Career Title, Career Description, Career Code,
          then for each variable: "<Variable>: Band Code", "<Variable>: Rank Order"

        Rank Order may be left empty or 0 when the selected_assessment has
        no rank system defined (SRS §4.1.4 rule).

        Scoped out (edge cases not handled):
          - Two variables sharing the same title within one solution (the
            first match wins; ambiguous headers are not detected).
          - Non-CSV upload formats (e.g. .xlsx).
        """
        solution = self.get_object()
        band_defs = self._solution_band_definitions(solution)

        base_cols = ["Career Stream", "Career Title", "Career Description", "Career Code"]

        if request.method == "GET":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="criteria_template_solution_{solution.id}.csv"'
            )
            writer = csv.writer(response)
            header = list(base_cols)
            for bd in band_defs:
                header += [f"{bd.section.title}: Band Code", f"{bd.section.title}: Rank Order"]
            writer.writerow(header)
            if band_defs:
                sample = ["IT Sector", "Computer Programmer", "", "ITCP"]
                for bd in band_defs:
                    first_code = bd.bands.order_by("band_number").values_list(
                        "band_code", flat=True
                    ).first()
                    sample += [first_code or "", ""]
                writer.writerow(sample)
            return response

        # POST: parse + create/update MappingCriterion rows
        if not band_defs:
            return Response(
                {
                    "error": {
                        "code": "not_ready",
                        "message": "No band definitions exist for this solution yet — "
                        "define bands for at least 2 variables before uploading criteria.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES.get("file")
        if not file:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "No file uploaded. Please upload a CSV file.",
                        "details": {"file": ["This field is required."]},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not file.name.endswith(".csv"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "File must be a CSV (.csv extension).",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            decoded = file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                decoded = file.read().decode("latin-1")
            except Exception as exc:
                return Response(
                    {"error": {"code": "validation_error", "message": f"Could not decode file: {exc}"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        reader = csv.DictReader(io.StringIO(decoded))
        actual_cols = {(c or "").strip().lower(): c for c in (reader.fieldnames or [])}

        def _find_col(*names):
            for name in names:
                col = actual_cols.get(name.strip().lower())
                if col:
                    return col
            return None

        career_title_col = _find_col("Career Title")
        if not career_title_col:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Missing required CSV column: 'Career Title'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        career_stream_col = _find_col("Career Stream")
        career_code_col = _find_col("Career Code")
        career_description_col = _find_col("Career Description")

        # Map each band_definition -> (band_code_col, rank_order_col, valid_codes)
        variable_cols = []
        unmatched_variables = []
        for bd in band_defs:
            band_col = _find_col(f"{bd.section.title}: Band Code")
            rank_col = _find_col(f"{bd.section.title}: Rank Order")
            if not band_col:
                unmatched_variables.append(bd.section.title)
                continue
            valid_codes = set(bd.bands.values_list("band_code", flat=True))
            variable_cols.append((bd, band_col, rank_col, valid_codes))

        created = 0
        updated = 0
        errors = []
        for row_num, row in enumerate(reader, start=2):
            career_title = (row.get(career_title_col) or "").strip()
            if not career_title or career_title.startswith("#"):
                continue
            career_stream = (row.get(career_stream_col) or "").strip() if career_stream_col else ""
            career_code = (row.get(career_code_col) or "").strip() if career_code_col else ""
            career_description = (
                (row.get(career_description_col) or "").strip() if career_description_col else ""
            )

            for bd, band_col, rank_col, valid_codes in variable_cols:
                band_code = (row.get(band_col) or "").strip()
                if not band_code:
                    continue  # variable not specified for this career — skip
                if band_code not in valid_codes:
                    errors.append(
                        {
                            "row": row_num,
                            "career_title": career_title,
                            "variable": bd.section.title,
                            "error": f"'{band_code}' is not a defined band code "
                            f"(valid: {sorted(valid_codes)}).",
                        }
                    )
                    continue

                rank_order_raw = (row.get(rank_col) or "").strip() if rank_col else ""
                rank_order = None
                if rank_order_raw and rank_order_raw != "0":
                    try:
                        rank_order = int(rank_order_raw)
                    except ValueError:
                        errors.append(
                            {
                                "row": row_num,
                                "career_title": career_title,
                                "variable": bd.section.title,
                                "error": f"Rank Order '{rank_order_raw}' is not a valid integer.",
                            }
                        )
                        continue

                _, is_created = MappingCriterion.objects.update_or_create(
                    solution=solution,
                    career_stream=career_stream,
                    career_title=career_title,
                    section=bd.section,
                    defaults={
                        "career_code": career_code,
                        "career_description": career_description,
                        "criterion_band_code": band_code,
                        "rank_order": rank_order,
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        return Response(
            {
                "message": f"Criteria upload complete: {created} created, {updated} updated, "
                f"{len(errors)} error(s).",
                "data": {
                    "created_count": created,
                    "updated_count": updated,
                    "error_count": len(errors),
                    "errors": errors,
                    "unmatched_variables": unmatched_variables,
                },
            },
            status=status.HTTP_200_OK,
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
