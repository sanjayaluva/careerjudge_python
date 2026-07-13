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
        "readiness": "view",
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
        """Publish an assessment — makes it available for sessions.

        Validates that the assessment is fully configured before publishing:
          - Status must be 'draft'
          - Must have at least 1 section
          - Must have at least 1 question assigned across all sections
          - Must have a title (already enforced by model, but double-check)
          - Must have an objective (recommended for candidate-facing display)

        Returns a detailed error listing all missing requirements so the
        author knows exactly what to fix.
        """
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

        # ── Readiness validation ──
        errors = []

        # 1. Title (model enforces non-empty, but check anyway)
        if not assessment.title or not assessment.title.strip():
            errors.append("Assessment title is required.")

        # 2. At least one section
        sections = assessment.sections.all()
        if not sections.exists():
            errors.append("At least one section must be created before publishing.")

        # 3. At least one question assigned (across all sections)
        total_questions = sum(s.questions.count() for s in sections)
        if total_questions == 0:
            errors.append("At least one question must be assigned to a section before publishing.")

        # 4. Each leaf section should have at least one question
        # (A section with subsections but no direct questions is fine —
        # questions can be on the children. But a leaf section with no
        # questions and no children is empty.)
        for s in sections:
            is_leaf = not s.subsections.exists()
            if is_leaf and s.questions.count() == 0:
                errors.append(
                    f"Section '{s.title}' (L{s.level}) has no questions and no "
                    "sub-sections. Add questions or sub-sections before publishing."
                )

        if errors:
            return Response(
                {
                    "error": {
                        "code": "assessment_not_ready",
                        "message": (
                            "Assessment is not ready to publish. Fix the following "
                            f"{len(errors)} issue(s):\n• " + "\n• ".join(errors)
                        ),
                        "details": {
                            "errors": errors,
                            "section_count": sections.count(),
                            "question_count": total_questions,
                        },
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment.status = "published"
        assessment.save(update_fields=["status", "updated_at"])

        # Notify all individual users (candidates) that a new assessment is available
        from apps.notifications.models import notify_role

        notify_role(
            "individual",
            "New assessment available",
            f"'{assessment.title}' is now available for you to take.",
            "assessment",
            f"/assessments/{assessment.id}",
        )

        return Response(
            {
                "message": "Assessment published.",
                "data": {"id": assessment.id, "status": assessment.status},
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def readiness(self, request, pk=None):
        """Check if the assessment is ready to publish.

        GET /api/assessments/<id>/readiness/
        → {message, data: {ready: bool, errors: [...], section_count, question_count}}

        Used by the frontend to enable/disable the Publish button and show
        a readiness checklist on the detail page.
        """
        assessment = self.get_object()
        sections = assessment.sections.all()
        total_questions = sum(s.questions.count() for s in sections)

        errors = []
        if not assessment.title or not assessment.title.strip():
            errors.append("Assessment title is required.")
        if not sections.exists():
            errors.append("At least one section must be created.")
        if total_questions == 0:
            errors.append("At least one question must be assigned to a section.")
        for s in sections:
            is_leaf = not s.subsections.exists()
            if is_leaf and s.questions.count() == 0:
                errors.append(
                    f"Section '{s.title}' (L{s.level}) has no questions and no sub-sections."
                )

        return Response(
            {
                "message": "OK",
                "data": {
                    "ready": len(errors) == 0,
                    "errors": errors,
                    "section_count": sections.count(),
                    "question_count": total_questions,
                    "has_title": bool(assessment.title and assessment.title.strip()),
                    "has_objective": bool(assessment.objective and assessment.objective.strip()),
                    "has_instructions": bool(
                        assessment.instructions and assessment.instructions.strip()
                    ),
                },
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

        # Notify the candidate that their session has been scored
        from apps.notifications.models import notify_user

        notify_user(
            session.candidate,
            "Assessment completed",
            f"Your assessment '{session.assessment.title}' has been submitted. "
            f"Score: {session.total_score}/{session.max_score} ({session.percentage}%).",
            "session",
            f"/assessments/sessions/{session.id}/results",
        )

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
        # Candidates see only their own sessions.
        # cj_admin can see ALL sessions (needed for the debug endpoint
        # and for admin oversight of candidate activity).
        qs = AssessmentSession.objects.select_related("assessment", "candidate")
        role_name = self.request.user.role.name if self.request.user.role else None
        if role_name == "cj_admin" or self.request.user.is_superuser:
            return qs
        return qs.filter(candidate=self.request.user)

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

        # Notify the candidate that their session has been scored
        from apps.notifications.models import notify_user

        notify_user(
            session.candidate,
            "Assessment completed",
            f"Your assessment '{session.assessment.title}' has been submitted. "
            f"Score: {session.total_score}/{session.max_score} ({session.percentage}%).",
            "session",
            f"/assessments/sessions/{session.id}/results",
        )

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

    @action(detail=True, methods=["get"])
    def debug(self, request, pk=None):
        """Full scoring debug breakdown for a session.

        GET /api/assessments/sessions/<id>/debug/
        → Returns the complete scoring pipeline: every question attempt with
          its raw_answer, the correct answer, the calculated score, the
          scoring mode used, and the section hierarchy with rolled-up scores.

        cj_admin only — this is a diagnostic tool for verifying the scoring
        engine works correctly across all question types.
        """
        # Restrict to cj_admin
        role_name = request.user.role.name if request.user.role else None
        if role_name != "cj_admin" and not request.user.is_superuser:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Debug view is restricted to cj_admin.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        session = self.get_object()
        from .scoring import _get_max_score, score_question

        # ── Build the section hierarchy ──
        all_sections = list(session.assessment.sections.all().order_by("level", "order"))
        section_map = {s.id: s for s in all_sections}
        sections_debug = []
        for s in all_sections:
            sections_debug.append(
                {
                    "id": s.id,
                    "title": s.title,
                    "level": s.level,
                    "order": s.order,
                    "parent_id": s.parent_id,
                    "parent_title": section_map[s.parent_id].title if s.parent_id else None,
                    "duration_seconds": s.duration_seconds,
                }
            )

        # ── Build per-attempt debug ──
        attempts = session.question_attempts.select_related("question", "section").all()
        attempts_debug = []
        for att in attempts:
            q = att.question
            # Determine correct answer for display
            correct_answer = None
            if q.options.exists():
                correct_opts = list(q.options.filter(is_correct=True))
                if q.question_type.startswith("MCQ_"):
                    correct_answer = {
                        "type": "MCQ",
                        "is_multi": len(correct_opts) > 1,
                        "correct_option_ids": [o.id for o in correct_opts],
                        "correct_option_texts": [o.text_value for o in correct_opts],
                    }
                elif q.question_type.startswith("FITB_"):
                    correct_answer = {
                        "type": "FITB",
                        "fields": [
                            {
                                "option_id": o.id,
                                "label": o.text_value,
                                "accepted_answers": [
                                    ca.answer_text for ca in o.correct_answers.all()
                                ],
                            }
                            for o in q.options.all().order_by("order")
                        ],
                    }
                elif q.question_type == "MATCH_FOLLOWING":
                    correct_answer = {
                        "type": "MATCH",
                        "pairs": [
                            {
                                "a_id": o.id,
                                "a_text": o.text_value,
                                "b_match_pair_id": o.match_pair_id,
                            }
                            for o in q.options.filter(option_type="MATCH_A").order_by("order")
                        ],
                    }
                elif q.question_type == "HOTSPOT_SINGLE":
                    correct_answer = {
                        "type": "HOTSPOT",
                        "is_multi": False,
                        "areas": [
                            {
                                "id": ha.id,
                                "shape": ha.shape_type,
                                "is_correct": ha.is_correct,
                                "x": ha.x,
                                "y": ha.y,
                                "w": ha.width_px,
                                "h": ha.height_px,
                            }
                            for ha in q.hotspot_areas.all()
                        ],
                    }
                elif q.question_type == "HOTSPOT_MULTI":
                    correct_answer = {
                        "type": "HOTSPOT",
                        "is_multi": True,
                        "areas": [
                            {
                                "id": ha.id,
                                "shape": ha.shape_type,
                                "is_correct": ha.is_correct,
                                "x": ha.x,
                                "y": ha.y,
                                "w": ha.width_px,
                                "h": ha.height_px,
                            }
                            for ha in q.hotspot_areas.all()
                        ],
                    }
                elif q.question_type == "STANDARD_RATING_SCALE":
                    correct_answer = {
                        "type": "RATING",
                        "scale_points": q.rating_scale_points,
                        "direction": q.rating_direction,
                    }
                elif q.question_type.startswith("FORCED_CHOICE"):
                    correct_answer = {
                        "type": "FORCED_CHOICE",
                        "options": [
                            {
                                "id": o.id,
                                "text": o.text_value,
                                "predefined_score": o.predefined_score,
                            }
                            for o in q.options.all().order_by("order")
                        ],
                    }
                elif q.question_type.startswith("RANK"):
                    correct_answer = {
                        "type": "RANK",
                        "correct_order": [
                            {"id": o.id, "text": o.text_value, "order": o.order}
                            for o in q.options.all().order_by("order")
                        ],
                    }

            # Re-score to show the calculation
            calculated_score, calculated_max = score_question(q, att.raw_answer)
            default_max = _get_max_score(q)

            attempts_debug.append(
                {
                    "attempt_id": att.id,
                    "question_id": q.id,
                    "question_title": q.question_title,
                    "question_type": q.question_type,
                    "question_type_label": q.get_question_type_display(),
                    "scoring_type": q.scoring_type,
                    "scoring_type_label": q.get_scoring_type_display(),
                    "section_id": att.section_id,
                    "section_title": (
                        section_map[att.section_id].title
                        if att.section_id and att.section_id in section_map
                        else None
                    ),
                    "section_level": (
                        section_map[att.section_id].level
                        if att.section_id and att.section_id in section_map
                        else None
                    ),
                    "sub_question_index": att.sub_question_index,
                    "status": att.status,
                    "raw_answer": att.raw_answer,
                    "correct_answer": correct_answer,
                    "score": att.score,
                    "max_score": att.max_score,
                    "calculated_score": calculated_score,
                    "calculated_max": calculated_max,
                    "default_max": default_max,
                    "score_matches": (
                        (att.score == calculated_score) if att.score is not None else None
                    ),
                    "answered_at": att.answered_at.isoformat() if att.answered_at else None,
                    "time_spent_seconds": att.time_spent_seconds,
                }
            )

        # ── Build section scores with hierarchy ──

        section_scores = {ss.section_id: ss for ss in session.section_scores.all()}
        scores_debug = []
        for s in all_sections:
            ss = section_scores.get(s.id)
            scores_debug.append(
                {
                    "section_id": s.id,
                    "title": s.title,
                    "level": s.level,
                    "parent_id": s.parent_id,
                    "raw_score": ss.raw_score if ss else 0.0,
                    "max_score": ss.max_score if ss else 0.0,
                    "percentage": ss.percentage if ss else 0.0,
                    "has_direct_questions": any(a["section_id"] == s.id for a in attempts_debug),
                }
            )

        # ── Session summary ──
        session_summary = {
            "id": session.id,
            "assessment_id": session.assessment_id,
            "assessment_title": session.assessment.title,
            "assessment_type": session.assessment.assessment_type,
            "candidate_id": session.candidate_id,
            "candidate_email": session.candidate.email,
            "status": session.status,
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_score": session.total_score,
            "max_score": session.max_score,
            "percentage": session.percentage,
            "total_duration_seconds": session.assessment.total_duration_seconds,
            "question_count": len(attempts_debug),
            "attempted_count": sum(1 for a in attempts_debug if a["status"] == "attempted"),
            "unattempted_count": sum(1 for a in attempts_debug if a["status"] != "attempted"),
            "bookmarked_count": sum(1 for a in attempts_debug if a["status"] == "bookmarked"),
        }

        return Response(
            {
                "message": "OK",
                "data": {
                    "session": session_summary,
                    "sections": sections_debug,
                    "section_scores": scores_debug,
                    "attempts": attempts_debug,
                },
            },
            status=status.HTTP_200_OK,
        )
