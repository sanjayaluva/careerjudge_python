"""Views for the Assessment module.

Endpoints
----------
Assessments (admin/author):
  GET    /api/assessments/                              — list (filterable by status)
  POST   /api/assessments/                              — create
  GET    /api/assessments/<id>/                         — retrieve (with sections)
  PATCH  /api/assessments/<id>/                         — update (draft only)
  DELETE /api/assessments/<id>/                         — delete (draft only)
  POST   /api/assessments/<id>/publish/                 — publish assessment
  GET    /api/assessments/<id>/sessions/                — list sessions for assessment
  POST   /api/assessments/<id>/start_session/           — start/resume a session

Sections (nested under assessment):
  GET    /api/assessments/<aid>/sections/               — list sections
  POST   /api/assessments/<aid>/sections/               — create section
  PATCH  /api/assessments/<aid>/sections/<id>/          — update section
  DELETE /api/assessments/<aid>/sections/<id>/          — delete section

Questions (nested under section):
  GET    /api/assessments/<aid>/sections/<sid>/questions/   — list assigned questions
  POST   /api/assessments/<aid>/sections/<sid>/questions/   — assign question
  DELETE /api/assessments/<aid>/sections/<sid>/questions/<id>/  — remove question

Sessions (candidate-facing):
  GET    /api/assessments/sessions/                     — list my sessions
  GET    /api/assessments/sessions/<id>/                — retrieve session
  GET    /api/assessments/sessions/<id>/questions/      — get questions for session
  POST   /api/assessments/sessions/<id>/answer/         — save answer for one question
  POST   /api/assessments/sessions/<id>/submit/         — submit entire session
  POST   /api/assessments/sessions/<id>/suspend/        — suspend session
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.mixins import ActionSerializerMixin
from core.permissions import HasModulePermission

from .models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
    QuestionAttempt,
)
from .serializers import (
    AssessmentListSerializer,
    AssessmentQuestionSerializer,
    AssessmentSectionSerializer,
    AssessmentSerializer,
    AssessmentSessionSerializer,
    QuestionAttemptSerializer,
)


class HasAssessmentPermission(HasModulePermission):
    module = "assessment"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
        "start_session": "view",
        "submit_session": "view",
        "publish": "change",
    }


class AssessmentViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for assessments.

    GET    /api/assessments/
    POST   /api/assessments/
    GET    /api/assessments/<id>/
    PATCH  /api/assessments/<id>/
    DELETE /api/assessments/<id>/
    POST   /api/assessments/<id>/publish/
    GET    /api/assessments/<id>/sessions/
    POST   /api/assessments/<id>/start_session/
    """

    queryset = Assessment.objects.select_related("created_by").prefetch_related(
        "sections", "sessions"
    )
    permission_classes = [IsAuthenticated, HasAssessmentPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "objective", "description"]
    ordering_fields = ["created_at", "title", "status"]
    ordering = ["-created_at"]

    serializer_class = AssessmentSerializer
    serializer_classes = {
        "list": AssessmentListSerializer,
    }

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        # Filter by status
        qstatus = params.get("status")
        if qstatus:
            qs = qs.filter(status=qstatus)

        # Role-based visibility: only assessment managers (cj_admin,
        # psychometrician, corp_admin, corp_exclusive) can see non-published
        # assessments. All other roles (individual, sme, reviewer, trainer,
        # group_admin, counsellor, channel_partner) only see published ones.
        # This applies to list + retrieve — candidates shouldn't be able to
        # open a draft assessment by ID either.
        if self.request.user.is_authenticated:
            role_name = self.request.user.role.name if self.request.user.role else None
            is_manager = (
                role_name
                in (
                    "cj_admin",
                    "psychometrician",
                    "corp_admin",
                    "corp_exclusive",
                )
                or self.request.user.is_superuser
            )
            if not is_manager:
                qs = qs.filter(status="published")

        return qs

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
                "message": "Assessment created.",
                "data": AssessmentSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        # Per SRS 03_assessment_configuration.json §2.2: "After going live,
        # user cannot directly edit Assessment Title. An edit request is sent
        # to Admin for approval."
        #
        # Interpretation: non-admin users cannot edit published assessments
        # (they must archive first). cj_admin can override and edit any
        # assessment regardless of status — this is the "Admin approval"
        # path described in the SRS.
        is_admin = request.user.is_superuser or (
            request.user.role and request.user.role.name == "cj_admin"
        )
        if (
            instance.status == "published"
            and request.data.get("status") != "archived"
            and not is_admin
        ):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": (
                            "Cannot edit a published assessment. Archive it first, "
                            "or contact a CareerJudge Admin to make the edit."
                        ),
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Assessment updated.", "data": AssessmentSerializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Same admin-override rule as update(): cj_admin can delete a
        # published assessment; everyone else must archive first.
        is_admin = request.user.is_superuser or (
            request.user.role and request.user.role.name == "cj_admin"
        )
        if instance.status == "published" and not is_admin:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Cannot delete a published assessment. Archive it first.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return Response({"message": "Assessment deleted.", "data": {}}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish an assessment — makes it available for sessions."""
        assessment = self.get_object()
        if assessment.status != "draft":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Assessment must be in 'draft' status to publish. Current: '{assessment.status}'",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        assessment.status = "published"
        assessment.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "message": "Assessment published.",
                "data": {"id": assessment.id, "status": assessment.status},
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def sessions(self, request, pk=None):
        """List all sessions for this assessment."""
        assessment = self.get_object()
        sessions = assessment.sessions.select_related("candidate").all()
        serializer = AssessmentSessionSerializer(sessions, many=True)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def start_session(self, request, pk=None):
        """Start a new assessment session for the current user."""
        assessment = self.get_object()
        if assessment.status != "published":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Assessment must be published to start a session.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # First, check for an existing active/suspended session to resume.
        # This takes priority over attempt_rule restrictions — resuming your
        # own in-flight session is always allowed.
        existing_sessions = AssessmentSession.objects.filter(
            assessment=assessment, candidate=request.user
        )
        existing = existing_sessions.filter(status__in=["active", "suspended"]).first()
        if existing:
            if existing.status == "suspended":
                existing.status = "active"
                existing.resumed_at = timezone.now()
                existing.save(update_fields=["status", "resumed_at"])
            return Response(
                {
                    "message": "Resuming existing session.",
                    "data": AssessmentSessionSerializer(existing).data,
                },
                status=status.HTTP_200_OK,
            )

        # No resumable session — enforce attempt rules before creating a new one.
        if existing_sessions.exists():
            if assessment.attempt_rule == "SINGLE_RETAKE":
                return Response(
                    {
                        "error": {
                            "code": "forbidden",
                            "message": "Multiple retakes not allowed for this assessment.",
                            "details": {},
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            if (
                assessment.attempt_rule == "SINGLE_SESSION"
                and existing_sessions.filter(status__in=["active", "completed"]).exists()
            ):
                return Response(
                    {
                        "error": {
                            "code": "forbidden",
                            "message": "Single session only. You already have an active or completed session.",
                            "details": {},
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Create new session
        session = AssessmentSession.objects.create(
            assessment=assessment,
            candidate=request.user,
            status="active",
        )

        # Pre-create QuestionAttempt records for all questions in the assessment
        sections = assessment.sections.all().order_by("level", "order")
        for section in sections:
            for aq in section.questions.all().order_by("order"):
                QuestionAttempt.objects.get_or_create(
                    session=session,
                    question=aq.question,
                    sub_question_index=aq.sub_question_index,
                    defaults={
                        "section": section,
                        "status": "not_attempted",
                    },
                )

        return Response(
            {
                "message": "Session started.",
                "data": AssessmentSessionSerializer(session).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit_session(self, request, pk=None):
        """Submit/complete an assessment session (alternate endpoint on assessment).

        Prefer ``/api/assessments/sessions/<id>/submit/`` — kept for backwards compat.
        """
        assessment = self.get_object()
        session = get_object_or_404(
            AssessmentSession,
            assessment=assessment,
            candidate=request.user,
            status="active",
        )

        # Mark session as completed
        session.status = "completed"
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "completed_at"])

        # Calculate scores using the scoring engine
        from .scoring import calculate_session_scores

        session = calculate_session_scores(session)

        return Response(
            {
                "message": "Session submitted.",
                "data": AssessmentSessionSerializer(session).data,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Assessment Section ViewSet
# ---------------------------------------------------------------------------


class AssessmentSectionViewSet(ModelViewSet):
    """CRUD for assessment sections (variable structure).

    GET    /api/assessments/<aid>/sections/
    POST   /api/assessments/<aid>/sections/
    PATCH  /api/assessments/<aid>/sections/<id>/
    DELETE /api/assessments/<aid>/sections/<id>/
    """

    serializer_class = AssessmentSectionSerializer
    permission_classes = [IsAuthenticated, HasAssessmentPermission]

    def get_queryset(self):
        aid = self.kwargs.get("assessment_id")
        return AssessmentSection.objects.filter(assessment_id=aid)

    def perform_create(self, serializer):
        aid = self.kwargs.get("assessment_id")
        assessment = get_object_or_404(Assessment, id=aid)
        serializer.save(assessment=assessment)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Section created.",
                "data": AssessmentSectionSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """PATCH/PUT /api/assessments/<aid>/sections/<id>/"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "Section updated.",
                "data": AssessmentSectionSerializer(serializer.instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        """DELETE /api/assessments/<aid>/sections/<id>/

        Cascades to subsections and any assigned AssessmentQuestion rows.
        """
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Section deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Assessment Question ViewSet
# ---------------------------------------------------------------------------


class AssessmentQuestionViewSet(ModelViewSet):
    """CRUD for assigning questions to sections.

    GET    /api/assessments/<aid>/sections/<sid>/questions/
    POST   /api/assessments/<aid>/sections/<sid>/questions/
    DELETE /api/assessments/<aid>/sections/<sid>/questions/<id>/
    """

    serializer_class = AssessmentQuestionSerializer
    permission_classes = [IsAuthenticated, HasAssessmentPermission]

    def get_queryset(self):
        sid = self.kwargs.get("section_id")
        return AssessmentQuestion.objects.filter(section_id=sid)

    def perform_create(self, serializer):
        sid = self.kwargs.get("section_id")
        section = get_object_or_404(AssessmentSection, id=sid)
        serializer.save(section=section)

    def create(self, request, *args, **kwargs):
        """Assign a question to a section.

        Enforces the assessment_type ↔ question_category rule:
          - normal assessments accept only normal questions
            (MCQ/FITB/Match/Grid/Hotspot)
          - psychometric assessments accept only psychometric questions
            (Rating/Rank/Rank-then-Rate/Forced-Choice)

        Per SRS 03_assessment_configuration.json §4.1 vs §4.2, mixing the two
        categories in a single assessment is not allowed.
        """
        from apps.question_bank.models import Question

        sid = self.kwargs.get("section_id")
        section = get_object_or_404(AssessmentSection, id=sid)
        assessment = section.assessment

        question_id = request.data.get("question")
        if not question_id:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "question is required.",
                        "details": {"question": ["This field is required."]},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        question = get_object_or_404(Question, id=question_id)

        # Type-mismatch check: normal vs psychometric
        question_cat = question.question_category  # 'normal' or 'psychometric'
        if question_cat != assessment.assessment_type:
            return Response(
                {
                    "error": {
                        "code": "question_category_mismatch",
                        "message": (
                            f"Cannot attach a {question_cat} question to a "
                            f"{assessment.assessment_type} assessment. "
                            "Normal and psychometric questions cannot be mixed "
                            "in the same assessment."
                        ),
                        "details": {
                            "assessment_type": assessment.assessment_type,
                            "question_category": question_cat,
                            "question_type": question.question_type,
                        },
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Question assigned to section.",
                "data": AssessmentQuestionSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Session ViewSet (for candidates)
# ---------------------------------------------------------------------------


class SessionViewSet(ModelViewSet):
    """Candidate-facing session endpoints.

    GET    /api/assessments/sessions/                    — list my sessions
    GET    /api/assessments/sessions/<id>/                — session detail
    GET    /api/assessments/sessions/<id>/questions/      — get questions for session
    POST   /api/assessments/sessions/<id>/answer/         — save answer for a question
    POST   /api/assessments/sessions/<id>/submit/         — submit entire session
    POST   /api/assessments/sessions/<id>/suspend/        — suspend session
    GET    /api/assessments/sessions/<id>/section_scores/ — section score breakdown
    """

    serializer_class = AssessmentSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Candidates see only their own sessions
        return AssessmentSession.objects.filter(candidate=self.request.user).select_related(
            "assessment", "candidate"
        )

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def questions(self, request, pk=None):
        """Get all questions for this session (with attempts)."""
        session = self.get_object()
        attempts = session.question_attempts.select_related("question", "section").all()
        serializer = QuestionAttemptSerializer(attempts, many=True)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        """Save an answer for a single question (or mark bookmark/skipped).

        Payload:
          - question_id: int (required)
          - sub_question_index: int (default 0)
          - raw_answer: dict (optional — omit to mark as skipped)
          - bookmark: bool (optional — marks as bookmarked)
        """
        session = self.get_object()
        if session.status != "active":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Session is {session.status}. Only active sessions can accept answers.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        question_id = request.data.get("question_id")
        sub_question_index = request.data.get("sub_question_index", 0)
        raw_answer = request.data.get("raw_answer")
        bookmark = request.data.get("bookmark", False)

        attempt = get_object_or_404(
            QuestionAttempt,
            session=session,
            question_id=question_id,
            sub_question_index=sub_question_index,
        )

        if raw_answer is not None:
            attempt.raw_answer = raw_answer
            attempt.status = "attempted"
            attempt.answered_at = timezone.now()
        elif bookmark:
            attempt.status = "bookmarked"
        else:
            attempt.status = "skipped"

        attempt.save()
        return Response(
            {
                "message": "Answer saved.",
                "data": QuestionAttemptSerializer(attempt).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit the entire session — calculate scores and complete.

        Returns:
            {
              "message": "...",
              "data": {
                "session": {...},
                "section_scores": [{section_title, raw_score, max_score, percentage}, ...]
              }
            }
        """
        session = self.get_object()
        if session.status != "active":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Session is {session.status}. Only active sessions can be submitted.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        session.status = "completed"
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "completed_at"])

        # Calculate scores using the scoring engine
        from .scoring import calculate_session_scores

        session = calculate_session_scores(session)

        # Get section scores for the response
        section_scores = session.section_scores.select_related("section").all()
        from .serializers import SectionScoreSerializer

        return Response(
            {
                "message": "Session submitted successfully.",
                "data": {
                    "session": AssessmentSessionSerializer(session).data,
                    "section_scores": SectionScoreSerializer(section_scores, many=True).data,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        """Suspend the session (candidate can resume later if attempt_rule allows)."""
        session = self.get_object()
        if session.status != "active":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only active sessions can be suspended.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        session.status = "suspended"
        session.suspended_at = timezone.now()
        session.save(update_fields=["status", "suspended_at"])

        return Response(
            {
                "message": "Session suspended. You can resume later.",
                "data": AssessmentSessionSerializer(session).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def section_scores(self, request, pk=None):
        """Return the per-section score breakdown for a completed session.

        GET /api/assessments/sessions/<id>/section_scores/
        → {message, data: [{section, section_title, raw_score, max_score, percentage}, ...]}
        """
        session = self.get_object()
        from .serializers import SectionScoreSerializer

        scores = session.section_scores.select_related("section").all()
        return Response(
            {"message": "OK", "data": SectionScoreSerializer(scores, many=True).data},
            status=status.HTTP_200_OK,
        )
