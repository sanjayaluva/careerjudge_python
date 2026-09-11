"""Views for the question_bank module."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.mixins import ActionSerializerMixin
from core.permissions import HasModulePermission

from .models import Category, Question, QuestionBankDeletionRequest
from .serializers import (
    CategorySerializer,
    CategoryTreeSerializer,
    QuestionBankDeletionRequestSerializer,
    QuestionCreateSerializer,
    QuestionDetailSerializer,
    QuestionListSerializer,
    QuestionReviewCreateSerializer,
    QuestionReviewSerializer,
)


class HasQuestionBankPermission(HasModulePermission):
    module = "question_bank"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
        "tree": "view",
        "submit_for_review": "change",
        "validate_config": "view",
        "psychometric_analysis": "change",  # psychometrician-only: computes indices
        # QuestionBankDeletionRequestViewSet custom actions (D1 §2.2/§4.3)
        "approve": "change",
        "decline": "change",
    }


def _is_qb_admin(user) -> bool:
    """cj_admin (or superuser) bypasses the deletion-request workflow."""
    role_name = user.role.name if user.role_id else None
    return bool(user.is_superuser or role_name == "cj_admin")


# ---------------------------------------------------------------------------
# Category ViewSet
# ---------------------------------------------------------------------------


class CategoryViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for question bank categories.

    GET    /api/question-bank/categories/
    POST   /api/question-bank/categories/
    GET    /api/question-bank/categories/<id>/
    PATCH  /api/question-bank/categories/<id>/
    DELETE /api/question-bank/categories/<id>/
    GET    /api/question-bank/categories/tree/  (tree view)
    """

    queryset = Category.objects.all()
    permission_classes = [IsAuthenticated, HasQuestionBankPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    serializer_class = CategorySerializer
    serializer_classes = {
        "tree": CategoryTreeSerializer,
    }

    def get_queryset(self):
        qs = super().get_queryset()
        parent = self.request.query_params.get("parent")
        if parent == "root":
            qs = qs.filter(parent__isnull=True)
        elif parent:
            qs = qs.filter(parent_id=parent)
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Category created.", "data": CategorySerializer(serializer.instance).data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Category updated.", "data": CategorySerializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # D1 §2.2: a non-admin's delete is NOT applied immediately — it
        # creates a pending QuestionBankDeletionRequest for CJ Admin to
        # review. cj_admin deletes directly (override).
        if not _is_qb_admin(request.user):
            reason = (request.data.get("reason") or "").strip()
            if not reason:
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": "reason is required to request deletion.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            dr = QuestionBankDeletionRequest.objects.create(
                target_type="category",
                target_id=instance.id,
                target_label=instance.name,
                requester=request.user,
                reason=reason,
            )
            return Response(
                {
                    "message": "Deletion request submitted. An admin will review it.",
                    "data": QuestionBankDeletionRequestSerializer(dr).data,
                },
                status=status.HTTP_201_CREATED,
            )
        instance.delete()
        return Response({"message": "Category deleted.", "data": {}}, status=status.HTTP_200_OK)

    # Custom action: tree view
    from rest_framework.decorators import action

    @action(detail=False, methods=["get"])
    def tree(self, request):
        roots = Category.objects.filter(parent__isnull=True, is_active=True).order_by("name")
        serializer = CategoryTreeSerializer(roots, many=True)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Question ViewSet
# ---------------------------------------------------------------------------


class QuestionViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for questions.

    GET    /api/question-bank/questions/
    POST   /api/question-bank/questions/
    GET    /api/question-bank/questions/<id>/
    PATCH  /api/question-bank/questions/<id>/
    DELETE /api/question-bank/questions/<id>/
    POST   /api/question-bank/questions/<id>/submit-for-review/
    """

    queryset = Question.objects.select_related("category", "created_by").prefetch_related(
        "options", "media_files", "flash_items", "hotspot_areas", "reviews"
    )
    permission_classes = [IsAuthenticated, HasQuestionBankPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["question_text_1", "question_id_label", "question_text_2"]
    ordering_fields = ["created_at", "question_type", "status", "difficulty_level"]
    ordering = ["-created_at"]

    serializer_class = QuestionDetailSerializer
    serializer_classes = {
        "list": QuestionListSerializer,
    }

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        # Filter by category (includes subcategories)
        category = params.get("category")
        if category:
            qs = qs.filter(category_id=category)

        # Filter by question type
        qtype = params.get("question_type")
        if qtype:
            qs = qs.filter(question_type=qtype)

        # Filter by status
        qstatus = params.get("status")
        if qstatus:
            qs = qs.filter(status=qstatus)

        # Filter by difficulty
        difficulty = params.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty_level=difficulty)

        # Filter by created_by (opt-in "mine" view, e.g. for admins/psychometricians)
        mine = params.get("mine")
        if mine == "true" and self.request.user.is_authenticated:
            qs = qs.filter(created_by=self.request.user)

        # Report 3 §4.1/§4.2 + D1 §3.1: trainers and SMEs author questions but
        # must ALWAYS see ONLY their own questions (not the full CJ Question
        # Bank pool) — this is not opt-in via ?mine=true. Reviewers may only
        # see their own questions plus questions that have actually entered
        # the review pipeline (i.e. not another user's private drafts).
        # Other roles (psychometrician, cj_admin) keep their existing access.
        if self.request.user.is_authenticated:
            role_name = self.request.user.role.name if self.request.user.role_id else None
            if role_name in ("trainer", "sme"):
                qs = qs.filter(created_by=self.request.user)
            elif role_name == "reviewer":
                qs = qs.filter(
                    Q(created_by=self.request.user) | ~Q(status="draft")
                )

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
        serializer = QuestionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Question created.",
                "data": QuestionDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # Editing rules:
        # - cj_admin can edit ANY question regardless of status (override).
        # - All other roles (SME, custom roles with 'change' permission) can
        #   only edit questions in 'draft' or 'sent_back' status. Once a
        #   question is submitted for review or confirmed/added to the
        #   question bank, it is locked for non-admin users.
        user_role_name = request.user.role.name if request.user.role_id else None
        is_admin = user_role_name == "cj_admin"
        if not is_admin and not instance.can_be_edited:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Question cannot be edited in '{instance.status}' status. "
                        f"Only draft or sent_back questions can be edited. "
                        f"CJ Admin can edit any question regardless of status.",
                        "details": {"current_status": instance.status},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Question updated.", "data": QuestionDetailSerializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Deleting rules mirror editing: cj_admin can delete any question
        # directly; other roles can only delete draft/sent_back questions,
        # and even then the delete is NOT applied immediately — it creates
        # a pending QuestionBankDeletionRequest for CJ Admin to review
        # (D1 §2.2/§4.3).
        is_admin = _is_qb_admin(request.user)
        if not is_admin:
            if not instance.can_be_edited:
                return Response(
                    {
                        "error": {
                            "code": "forbidden",
                            "message": f"Question cannot be deleted in '{instance.status}' status. "
                            f"CJ Admin can delete any question regardless of status.",
                            "details": {"current_status": instance.status},
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            reason = (request.data.get("reason") or "").strip()
            if not reason:
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": "reason is required to request deletion.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            dr = QuestionBankDeletionRequest.objects.create(
                target_type="question",
                target_id=instance.id,
                target_label=instance.question_title,
                requester=request.user,
                reason=reason,
            )
            return Response(
                {
                    "message": "Deletion request submitted. An admin will review it.",
                    "data": QuestionBankDeletionRequestSerializer(dr).data,
                },
                status=status.HTTP_201_CREATED,
            )
        instance.delete()
        return Response({"message": "Question deleted.", "data": {}}, status=status.HTTP_200_OK)

    from rest_framework.decorators import action

    @action(detail=True, methods=["post"])
    def submit_for_review(self, request, pk=None):
        """SME submits question for content review.

        Changes status from 'draft' or 'sent_back' to 'pending_content_review'.
        Validates that the question is fully configured before allowing submission.
        """
        from .validation import validate_question_config

        question = self.get_object()
        if question.status not in ("draft", "sent_back"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Question must be in 'draft' or 'sent_back' status to submit for review. "
                        f"Current status: '{question.status}'",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate configuration before submission
        errors = validate_question_config(question)
        if errors:
            return Response(
                {
                    "error": {
                        "code": "question_not_ready",
                        "message": "Question is not ready for review. Fix the following:\n• "
                        + "\n• ".join(errors),
                        "details": {"errors": errors},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        question.status = "pending_content_review"
        question.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "message": "Question submitted for content review.",
                "data": {"id": question.id, "status": question.status},
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def validate_config(self, request, pk=None):
        """Check if a question is fully configured for review submission.

        GET /api/question-bank/questions/<id>/validate_config/
        -> {message, data: {valid: bool, errors: [...]}}
        """
        from .validation import validate_question_config

        question = self.get_object()
        errors = validate_question_config(question)
        return Response(
            {
                "message": "OK",
                "data": {
                    "valid": len(errors) == 0,
                    "errors": errors,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def psychometric_analysis(self, request):
        """Run psychometric analysis on one or more questions (SRS 02).

        Triggered by the Psychometrician. Computes per-question:
          - Item Difficulty Index (IDI, TDI, BDI, DDI) for all questions
          - Item Discrimination Index for MCQ questions
          - Item-Total Correlation Index for non-MCQ questions

        Results are persisted on each Question (item_difficulty_index,
        top_group_difficulty_index, etc.) and returned in the response.

        Payload:
            {
                "question_ids": [1, 2, 3],         # required, list of question IDs
                "date_from": "2026-01-01",         # optional, ISO date
                "date_to": "2026-12-31",           # optional, ISO date
                "assessment_id": 42                # optional, filter by assessment
            }

        Returns:
            {
                "message": "Analysed N question(s).",
                "data": [
                    {
                        "question_id": 1,
                        "n_candidates": 50,
                        "item_difficulty_index": 0.62,
                        "top_group_difficulty_index": 0.85,
                        "bottom_group_difficulty_index": 0.32,
                        "difference_difficulty_index": 0.53,
                        "discrimination_index": 0.41,    # MCQ only, null otherwise
                        "item_total_correlation": null,  # non-MCQ only, null otherwise
                        "error": null                    # set if computation failed
                    },
                    ...
                ]
            }
        """
        from .psychometrics import run_psychometric_analysis

        question_ids = request.data.get("question_ids") or []
        if not question_ids or not isinstance(question_ids, list):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "question_ids (list of ints) is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        questions = list(Question.objects.filter(id__in=question_ids).select_related("category"))
        found_ids = {q.id for q in questions}
        missing = set(question_ids) - found_ids
        if missing:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": f"Question IDs not found: {sorted(missing)}",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse optional filters
        date_from = request.data.get("date_from")
        date_to = request.data.get("date_to")
        assessment_id = request.data.get("assessment_id")
        from datetime import datetime as _dt

        date_from_dt = _dt.fromisoformat(date_from) if date_from else None
        date_to_dt = _dt.fromisoformat(date_to) if date_to else None

        results = []
        for q in questions:
            r = run_psychometric_analysis(
                q,
                date_from=date_from_dt,
                date_to=date_to_dt,
                assessment_id=assessment_id,
            )
            results.append(
                {
                    "question_id": r.question_id,
                    "n_candidates": r.n_candidates,
                    "item_difficulty_index": r.item_difficulty_index,
                    "top_group_difficulty_index": r.top_group_difficulty_index,
                    "bottom_group_difficulty_index": r.bottom_group_difficulty_index,
                    "difference_difficulty_index": r.difference_difficulty_index,
                    "discrimination_index": r.discrimination_index,
                    "item_total_correlation": r.item_total_correlation,
                    "error": r.error,
                }
            )

        return Response(
            {
                "message": f"Analysed {len(results)} question(s).",
                "data": results,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------


class QuestionReviewView(APIView):
    """POST /api/question-bank/questions/<id>/review/ — submit a review action.

    Reviewer can approve/send_back content reviews.
    Psychometrician can approve/send_back psychometric reviews.

    The review_type determines which stage this is for:
    - 'content' → Reviewer's content review
    - 'psychometric' → Psychometrician's psychometric review
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, question_id):
        question = get_object_or_404(Question, id=question_id)

        # Check permissions based on review_type
        review_type = request.data.get("review_type")
        if not review_type:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "review_type is required (content or psychometric).",
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check user has permission to review
        if not request.user.has_module_right("question_bank", "review"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You do not have permission to review questions.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate question is in the right status for this review type
        if review_type == "content" and question.status != "pending_content_review":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Question must be in 'pending_content_review' status. Current: '{question.status}'",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if review_type == "psychometric" and question.status != "pending_psychometric_review":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Question must be in 'pending_psychometric_review' status. Current: '{question.status}'",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = QuestionReviewCreateSerializer(
            data={**request.data, "question": question.id},
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        review = serializer.save()

        # Refresh question from DB to get the updated status
        question.refresh_from_db()

        # If content review approved, move to psychometric review
        if review.action == "approve" and review_type == "content":
            question.status = "pending_psychometric_review"
            question.save(update_fields=["status", "updated_at"])

        # If psychometric review approved with exposure limit, set it
        if review.action == "approve" and review_type == "psychometric":
            exposure_limit = request.data.get("exposure_limit")
            if exposure_limit:
                question.exposure_limit = int(exposure_limit)
                question.save(update_fields=["exposure_limit", "updated_at"])
            question.refresh_from_db()

        return Response(
            {
                "message": f"Review {review.action}d.",
                "data": {
                    "review": QuestionReviewSerializer(review).data,
                    "question_status": question.status,
                },
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Question Review List View
# ---------------------------------------------------------------------------


class QuestionReviewListView(APIView):
    """GET /api/question-bank/questions/<id>/reviews/ — list all reviews for a question."""

    permission_classes = [IsAuthenticated]

    def get(self, request, question_id):
        question = get_object_or_404(Question, id=question_id)
        reviews = question.reviews.select_related("reviewer").all()
        serializer = QuestionReviewSerializer(reviews, many=True)
        return Response(
            {"message": "OK", "data": serializer.data},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Question Bank Deletion Request (D1 §2.2/§4.3) — admin approval workflow
# ---------------------------------------------------------------------------


class QuestionBankDeletionRequestViewSet(ModelViewSet):
    """List deletion requests + admin approve/decline actions.

    Requesters see only their own requests; admins see all. Approve/decline
    are admin-only and notify the requester of the decision.
    """

    queryset = QuestionBankDeletionRequest.objects.select_related("requester", "reviewed_by")
    permission_classes = [IsAuthenticated, HasQuestionBankPermission]
    serializer_class = QuestionBankDeletionRequestSerializer
    http_method_names = ["get", "head", "options", "post"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_qb_admin(user):
            return qs
        return qs.filter(requester=user)

    def list(self, request, *args, **kwargs):
        # Serialize directly (NOT super().list()) so pagination cannot wrap
        # the payload into {count, results} — the frontend expects an array.
        qs = self.filter_queryset(self.get_queryset())
        return Response(
            {"message": "OK", "data": self.get_serializer(qs, many=True).data},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        # Creation happens as a side effect of DELETE /categories/<id>/ or
        # DELETE /questions/<id>/ for non-admin users. Block direct creation
        # here to keep the audit trail clean.
        return Response(
            {
                "error": {
                    "code": "forbidden",
                    "message": "Submit requests via DELETE /categories/<id>/ or /questions/<id>/.",
                }
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _target_object(self, dr):
        model = Category if dr.target_type == "category" else Question
        return model.objects.filter(id=dr.target_id).first()

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Admin approves a deletion request — performs the real delete."""
        dr = self.get_object()
        if not _is_qb_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can approve."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if dr.status != "pending":
            return Response(
                {
                    "error": {
                        "code": "invalid_state",
                        "message": f"Request is already {dr.status}.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone

        dr.status = "approved"
        dr.reviewed_by = request.user
        dr.reviewed_at = timezone.now()
        dr.review_comment = request.data.get("admin_note", "")
        dr.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment"])

        # Perform the real delete. Snapshot the response data first, since
        # the target may not carry a FK back to this request.
        data = QuestionBankDeletionRequestSerializer(dr).data
        target = self._target_object(dr)
        if target is not None:
            target.delete()

        try:
            from apps.notifications.models import notify_user

            notify_user(
                dr.requester,
                f"Deletion approved: {dr.target_label or dr.target_type}",
                f"Your request to delete {dr.target_type} '{dr.target_label}' was approved and deleted.",
                "success",
                "/question-bank",
            )
        except Exception:
            pass
        return Response({"message": "Request approved.", "data": data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="decline")
    def decline(self, request, pk=None):
        """Admin declines a deletion request."""
        dr = self.get_object()
        if not _is_qb_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can decline."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if dr.status != "pending":
            return Response(
                {
                    "error": {
                        "code": "invalid_state",
                        "message": f"Request is already {dr.status}.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone

        dr.status = "rejected"
        dr.reviewed_by = request.user
        dr.reviewed_at = timezone.now()
        dr.review_comment = request.data.get("admin_note", "")
        dr.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment"])
        try:
            from apps.notifications.models import notify_user

            notify_user(
                dr.requester,
                f"Deletion request declined: {dr.target_label or dr.target_type}",
                f"Your request to delete {dr.target_type} '{dr.target_label}' was declined. "
                f"{dr.review_comment}",
                "warning",
                "/question-bank",
            )
        except Exception:
            pass
        return Response(
            {"message": "Request declined.", "data": QuestionBankDeletionRequestSerializer(dr).data},
            status=status.HTTP_200_OK,
        )
