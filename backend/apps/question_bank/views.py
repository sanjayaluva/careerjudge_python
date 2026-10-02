"""Views for the question_bank module."""

import csv
import logging

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.organizations.private_content import (
    can_author_private,
    in_space,
    is_private_author,
    require_same_space,
    resolve_owner_org_id,
    space_filter,
)
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

logger = logging.getLogger(__name__)


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
        "bulk_import": "add",  # E-QB-4: bulk full-question template import
        "submit_for_review": "change",
        "reviewer_options": "change",  # Report 9 #65: reviewer picker for submit_for_review
        "validate_config": "view",
        "psychometric_analysis": "change",  # psychometrician-only: computes indices
        "psychometric_extract": "change",  # Report 9 #87: extract/list step before a run
        # Manual psychometric-analysis path (D2) + filters (D2)
        "psychometric_data_download": "view",
        "psychometric_upload": "change",
        # Periodic QB updation / exposure setting (D1 §4.2/§4.3)
        "batch_status": "change",
        "batch_exposure_limit": "change",
        # QuestionBankDeletionRequestViewSet custom actions (D1 §2.2/§4.3)
        "approve": "change",
        "decline": "change",
    }


# Doc 1 §4.1.1: the analyses the Psychometrician can choose to run, and the
# Question fields each one produces.
PSYCHOMETRIC_ANALYSES = {
    "difficulty": (
        "item_difficulty_index",
        "top_group_difficulty_index",
        "bottom_group_difficulty_index",
        "difference_difficulty_index",
    ),
    "discrimination": ("discrimination_index",),
    "item_total": ("item_total_correlation",),
}


def _is_qb_admin(user) -> bool:
    """cj_admin (or superuser) bypasses the deletion-request workflow."""
    role_name = user.role.name if user.role_id else None
    return bool(user.is_superuser or role_name == "cj_admin")


def _deletes_directly(user, instance) -> bool:
    """CJ Admin deletes directly; so does a Corporate Exclusive Admin in his
    own organization's private question bank — he is the admin of that
    environment (Report 9 #39/#40), so no CJ deletion request applies."""
    return _is_qb_admin(user) or can_author_private(user, instance.owner_organization_id)


def _private_owner_for(request, category) -> int | None:
    """Owner organization for a new category / question: its parent category's
    space, else the author's own space (Report 9 #39/#40)."""
    if category is not None:
        if not in_space(request.user, category.owner_organization_id):
            raise ValidationError({"category": "Category not found."})
        return category.owner_organization_id
    return resolve_owner_org_id(request.user, request.data.get("owner_organization"))


def _domain_category_ids(root: Category) -> list[int]:
    """All category ids in a domain: the root and every descendant."""
    ids = [root.id]
    frontier = [root.id]
    while frontier:
        children = list(
            Category.objects.filter(parent_id__in=frontier).values_list("id", flat=True)
        )
        ids.extend(children)
        frontier = children
    return ids


def _pick_domain_reviewer(question):
    """Pick a Reviewer in the same domain as the question (E-X3).

    'Domain' is the top-level category (tree root). A reviewer is considered
    in-domain if they have authored a question anywhere in that domain's
    category subtree. Preference goes to in-domain reviewers; if none exist we
    fall back to any active reviewer. Among candidates the least-loaded (fewest
    questions currently assigned and pending content review) is chosen. The
    author is never assigned to review their own question. Returns a User or
    None when no reviewer is available.
    """
    from apps.accounts.models import User

    base = User.objects.filter(is_active=True, role__name="reviewer")
    if question.category_id:
        cat_ids = _domain_category_ids(question.category.domain_root)
        in_domain_ids = (
            Question.objects.filter(category_id__in=cat_ids, created_by__role__name="reviewer")
            .values_list("created_by_id", flat=True)
            .distinct()
        )
        candidates = base.filter(id__in=list(in_domain_ids))
        if not candidates.exists():
            candidates = base
    else:
        candidates = base
    candidates = candidates.exclude(id=question.created_by_id)
    reviewers = list(candidates)
    if not reviewers:
        return None
    return min(
        reviewers,
        key=lambda r: Question.objects.filter(
            assigned_reviewer=r, status="pending_content_review"
        ).count(),
    )


def _usable_reviewer(user, question) -> bool:
    """An active Reviewer who is not the question's author."""
    return (
        user is not None
        and user.is_active
        and user.role_id is not None
        and user.role.name == "reviewer"
        and user.id != question.created_by_id
    )


def _previous_reviewer(question):
    """Reviewer to route a resubmitted (sent-back) question to (Report 9 #71).

    Prefers the reviewer who last sent the question back at content review,
    then the reviewer it is still assigned to. Returns None when neither is an
    active Reviewer (other than the author), so the caller re-routes it.
    """
    from .models import QuestionReview

    last = (
        QuestionReview.objects.filter(question=question, review_type="content", action="send_back")
        .select_related("reviewer__role")
        .order_by("-created_at", "-id")
        .first()
    )
    if last and _usable_reviewer(last.reviewer, question):
        return last.reviewer
    if _usable_reviewer(question.assigned_reviewer, question):
        return question.assigned_reviewer
    return None


# Task statuses in which an SME is still working on (or finishing) a task.
_OPEN_TASK_STATUSES = ("pending", "in_progress", "overdue", "awaiting_review")


def _task_reviewer(question, author):
    """Reviewer CJ Admin named on the author's open SME task (Report 9 #65).

    When the SME has several open tasks naming a reviewer, the one whose
    specification covers the question's category wins (subcategory, then
    main category); otherwise the most recently assigned task. Returns None
    when no open task names a usable reviewer.
    """
    from apps.tasks.models import Task

    if author is None:
        return None
    tasks = list(
        Task.objects.filter(
            assigned_to=author,
            assignee_role="sme",
            status__in=_OPEN_TASK_STATUSES,
            reviewer__isnull=False,
        )
        .select_related("reviewer__role")
        .prefetch_related("specs")
        .order_by("-created_at", "-id")
    )
    tasks = [t for t in tasks if _usable_reviewer(t.reviewer, question)]
    if not tasks:
        return None
    if question.category_id:
        cat_name = question.category.name.strip().lower()
        root_name = question.category.domain_root.name.strip().lower()

        def score(task):
            best = 0
            for spec in task.specs.all():
                if spec.qb_subcategory and spec.qb_subcategory.strip().lower() == cat_name:
                    best = max(best, 2)
                elif spec.qb_category and spec.qb_category.strip().lower() in (
                    root_name,
                    cat_name,
                ):
                    best = max(best, 1)
            return best

        best_task = max(tasks, key=score)  # max keeps the first (newest) on ties
        return best_task.reviewer
    return tasks[0].reviewer


def _reviewer_label(user) -> dict:
    """A reviewer as shown in the SME's / CJ Admin's reviewer pickers."""
    profile = getattr(user, "profile", None)
    return {
        "id": user.id,
        "full_name": user.full_name or user.email,
        "email": user.email,
        # Report 9 #67/#69: domains of expertise shown next to the name.
        "domains_of_expertise": list(getattr(profile, "domains_of_expertise", None) or []),
    }


def _usable_psychometrician(user) -> bool:
    return (
        user is not None
        and user.is_active
        and user.role_id is not None
        and user.role.name == "psychometrician"
    )


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
        # Report 9 #39 / Report 4 §3: CJ's categories and each exclusive
        # organization's private categories never mix.
        qs = space_filter(super().get_queryset(), self.request.user)
        parent = self.request.query_params.get("parent")
        if parent == "root":
            qs = qs.filter(parent__isnull=True)
        elif parent:
            qs = qs.filter(parent_id=parent)
        return qs

    def perform_create(self, serializer):
        owner_id = _private_owner_for(self.request, serializer.validated_data.get("parent"))
        serializer.save(created_by=self.request.user, owner_organization_id=owner_id)

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
        parent = serializer.validated_data.get("parent")
        if parent is not None:
            require_same_space(
                instance.owner_organization_id, parent.owner_organization_id, "category"
            )
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
        if not _deletes_directly(request.user, instance):
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
        roots = space_filter(
            Category.objects.filter(parent__isnull=True, is_active=True), request.user
        ).order_by("name")
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
        # Report 9 #40 / Report 4 §3: CJ's question bank and each exclusive
        # organization's private question bank never mix.
        qs = space_filter(super().get_queryset(), self.request.user)
        params = self.request.query_params

        # Filter by category (includes subcategories)
        category = params.get("category")
        if category:
            root = Category.objects.filter(id=category).first()
            qs = qs.filter(category_id__in=_domain_category_ids(root) if root else [category])

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

        # Periodic QB updation (D1 §4.3): "Question Expiry" filter — surface
        # questions whose validity has lapsed (expired=true) or is still
        # valid / unset (expired=false).
        expired = params.get("expired")
        if expired == "true":
            qs = qs.filter(expires_at__lt=timezone.now())
        elif expired == "false":
            qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now()))

        # Filter by created_by (opt-in "mine" view, e.g. for admins/psychometricians)
        mine = params.get("mine")
        if mine == "true" and self.request.user.is_authenticated:
            qs = qs.filter(created_by=self.request.user)

        # E-X3: a reviewer's routed queue — questions assigned to them.
        # Report 9 #92: a psychometrician's queue is the questions routed
        # back to him after he sent them back.
        if params.get("assigned") == "me" and self.request.user.is_authenticated:
            user = self.request.user
            if user.role_id and user.role.name == "psychometrician":
                qs = qs.filter(assigned_psychometrician=user)
            else:
                qs = qs.filter(assigned_reviewer=user)

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
                qs = qs.filter(Q(created_by=self.request.user) | ~Q(status="draft"))

        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, **self._private_fields(serializer))

    def _private_fields(self, serializer) -> dict:
        """Report 9 #40: a question goes into its category's space (else the
        author's). A private question skips CJ's SME → Reviewer →
        Psychometrician workflow: it is in the organization's question bank
        ('confirmed') as soon as it is saved, ready for its assessments."""
        owner_id = _private_owner_for(self.request, serializer.validated_data.get("category"))
        if owner_id is None:
            return {}
        return {"owner_organization_id": owner_id, "status": "confirmed"}

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

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk-import full questions from a template (E-QB-4).

        Extends the single-question create (CJ_UC013) to a batch: the client
        posts {"questions": [<full question payload>, ...]} and each item is
        validated + created with the same serializer as a normal create. The
        response reports how many were created and per-row errors, so a partial
        template still imports its valid rows.

        Body: {"questions": [ {question_type, question_title, ...}, ... ]}
        """
        items = request.data.get("questions")
        if not isinstance(items, list) or not items:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Provide a non-empty 'questions' list.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created, errors = [], []
        for idx, payload in enumerate(items):
            serializer = QuestionCreateSerializer(data=payload, context={"request": request})
            if serializer.is_valid():
                serializer.save(created_by=request.user, **self._private_fields(serializer))
                created.append(serializer.instance.id)
            else:
                errors.append({"index": idx, "errors": serializer.errors})

        return Response(
            {
                "message": f"Imported {len(created)} of {len(items)} question(s).",
                "data": {
                    "created_count": len(created),
                    "created_ids": created,
                    "error_count": len(errors),
                    "errors": errors,
                },
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST,
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
        # Report 9 #40: the Corporate Exclusive Admin edits his private
        # questions in any status — he is the admin of that environment.
        is_admin = user_role_name == "cj_admin" or can_author_private(
            request.user, instance.owner_organization_id
        )
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
        category = serializer.validated_data.get("category")
        if category is not None:
            require_same_space(
                instance.owner_organization_id, category.owner_organization_id, "category"
            )
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
        is_admin = _deletes_directly(request.user, instance)
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
        if question.owner_organization_id:
            # Report 9 #40: private questions never enter CJ's review workflow.
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Your organization's questions are not sent for CJ review; "
                        "they are in your question bank as soon as they are saved.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
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

        # Report 9 #65: the SME picks the Reviewer to send the question to.
        chosen = None
        chosen_id = request.data.get("reviewer")
        if chosen_id not in (None, ""):
            from apps.accounts.models import User

            try:
                chosen = User.objects.select_related("role").filter(id=int(chosen_id)).first()
            except (TypeError, ValueError):
                chosen = None
            if not _usable_reviewer(chosen, question):
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": "Choose an active Reviewer to send the question to.",
                            "details": {"reviewer": chosen_id},
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        was_sent_back = question.status == "sent_back"
        question.status = "pending_content_review"
        # Report 9 #71: a sent-back question goes back to the SAME reviewer
        # who sent it back (the SME's picker shows it fixed). First
        # submissions go to the reviewer the SME chose (#65), else the one
        # named on his task, else - only as a fallback - the E-X3
        # same-domain least-busy reviewer.
        reviewer = _previous_reviewer(question) if was_sent_back else None
        if reviewer is None:
            reviewer = chosen or _task_reviewer(question, question.created_by)
        if reviewer is None:
            # E-X3: route to a Reviewer in the same domain (category tree root).
            reviewer = _pick_domain_reviewer(question)
        question.assigned_reviewer = reviewer
        question.save(update_fields=["status", "assigned_reviewer", "updated_at"])

        if reviewer:
            try:
                from apps.notifications.models import notify_user

                notify_user(
                    reviewer,
                    "Question assigned for review",
                    f"'{question.question_title}' was routed to you for content review.",
                    "info",
                    f"/question-bank/{question.id}",
                )
            except Exception as e:  # pragma: no cover - notification is best-effort
                logger.warning("Reviewer assignment notification failed: %s", e)

        return Response(
            {
                "message": "Question submitted for content review.",
                "data": {
                    "id": question.id,
                    "status": question.status,
                    "assigned_reviewer": reviewer.id if reviewer else None,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="reviewer-options")
    def reviewer_options(self, request, pk=None):
        """Reviewer picker for "Submit for review" (Report 9 #65).

        GET /api/question-bank/questions/<id>/reviewer-options/
        -> {
             "reviewers": [{id, full_name, email, domains_of_expertise}, ...],
             "default_reviewer": <id> | null,   # pre-selected in the picker
             "task_reviewer": <id> | null,      # named by CJ Admin on the SME's task
             "locked": bool,                    # sent back: returns to the same reviewer
           }

        The pool is every active Reviewer (never the question's author).
        """
        from apps.accounts.models import User

        question = self.get_object()
        pool = (
            User.objects.filter(is_active=True, role__name="reviewer")
            .exclude(id=question.created_by_id)
            .select_related("profile")
            .order_by("full_name", "email")
        )
        task_reviewer = _task_reviewer(question, question.created_by)
        previous = _previous_reviewer(question) if question.status == "sent_back" else None
        default = previous or task_reviewer
        return Response(
            {
                "message": "OK",
                "data": {
                    "reviewers": [_reviewer_label(u) for u in pool],
                    "default_reviewer": default.id if default else None,
                    "task_reviewer": task_reviewer.id if task_reviewer else None,
                    "locked": previous is not None,
                },
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

    # -----------------------------------------------------------------
    # Periodic QB updation + exposure setting (D1 §4.2/§4.3)
    # -----------------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="batch-status")
    def batch_status(self, request):
        """Batch activate/inactivate questions (D1 §4.3 Periodic QB Updation).

        Used both for "Removal/inactivation of Low-Quality questions" and
        "Activation of Expired Questions" — the caller extracts a question
        list with the regular list filters (e.g. ?expired=true), then posts
        the selected IDs here with the desired is_active value.

        POST /api/question-bank/questions/batch-status/
          body: {"question_ids": [1, 2, 3], "is_active": false}
        """
        question_ids = request.data.get("question_ids") or []
        if not question_ids or not isinstance(question_ids, list):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "question_ids (non-empty list of ints) is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "is_active" not in request.data:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "is_active (bool) is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        is_active = bool(request.data.get("is_active"))

        qs = space_filter(Question.objects.filter(id__in=question_ids), request.user)
        found_ids = set(qs.values_list("id", flat=True))
        missing = set(question_ids) - found_ids
        updated = qs.update(is_active=is_active, updated_at=timezone.now())

        return Response(
            {
                "message": f"{updated} question(s) set to "
                f"{'active' if is_active else 'inactive'}.",
                "data": {
                    "updated_count": updated,
                    "updated_ids": sorted(found_ids),
                    "missing_ids": sorted(missing),
                    "is_active": is_active,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="batch-exposure-limit")
    def batch_exposure_limit(self, request):
        """Batch-set the exposure limit for a set of questions (D1 §4.2
        Question Exposure Setting — "User views questions, sets exposure
        limit, and submits").

        The candidate-facing enforcement (auto-deactivation once
        exposure_count reaches exposure_limit) already exists in
        apps.assessment.scoring — this action only surfaces the bulk
        management operation for the Psychometrician.

        POST /api/question-bank/questions/batch-exposure-limit/
          body: {"question_ids": [1, 2, 3], "exposure_limit": 500}
          # exposure_limit may be null to clear the limit (unlimited exposure)
        """
        question_ids = request.data.get("question_ids") or []
        if not question_ids or not isinstance(question_ids, list):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "question_ids (non-empty list of ints) is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "exposure_limit" not in request.data:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "exposure_limit (int or null) is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        exposure_limit = request.data.get("exposure_limit")
        if exposure_limit is not None:
            try:
                exposure_limit = int(exposure_limit)
            except (TypeError, ValueError):
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": "exposure_limit must be an integer or null.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if exposure_limit < 1:
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": "exposure_limit must be >= 1 (or null to clear it).",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        qs = space_filter(Question.objects.filter(id__in=question_ids), request.user)
        found_ids = set(qs.values_list("id", flat=True))
        missing = set(question_ids) - found_ids
        updated = qs.update(exposure_limit=exposure_limit, updated_at=timezone.now())

        return Response(
            {
                "message": f"Exposure limit set to {exposure_limit} for {updated} question(s).",
                "data": {
                    "updated_count": updated,
                    "updated_ids": sorted(found_ids),
                    "missing_ids": sorted(missing),
                    "exposure_limit": exposure_limit,
                },
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------------------------------------------
    # Psychometric analysis — automatic + manual paths (SRS 02, D2)
    # -----------------------------------------------------------------

    def _resolve_psychometric_filters(self, data):
        """Shared filter parsing for the psychometric_analysis /
        psychometric_data_download actions (D2: date-range, assessment,
        category, region, age-range).

        Returns (questions, filters_dict, error_response). error_response is
        a Response to return immediately when validation fails, else None.
        """
        from datetime import datetime as _dt

        question_ids = data.get("question_ids") or []
        category_id = data.get("category_id")
        # Report 9 #87: Doc 1 §4.1.1 "Question ID" filter — free text of one
        # or more ids / display labels separated by commas or spaces.
        question_ref = str(data.get("question_ref") or "").strip()

        def _invalid(message):
            return (
                None,
                None,
                Response(
                    {"error": {"code": "validation_error", "message": message}},
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        if is_private_author(self.request.user):
            # Report 4 §3: psychometric analysis is not one of the exclusive
            # environment's rights.
            return _invalid("Psychometric analysis is not available in your organization's space.")

        if question_ids and not isinstance(question_ids, list):
            return _invalid("question_ids must be a list of ints.")

        if not question_ids and not category_id and not question_ref:
            return _invalid("question_ids (list of ints), category_id or question_ref is required.")

        # Report 4 §3: CJ's analysis never reaches an organization's private questions.
        qs = space_filter(Question.objects.select_related("category"), self.request.user)
        if question_ids:
            qs = qs.filter(id__in=question_ids)
            found_ids = set(qs.values_list("id", flat=True))
            missing = set(question_ids) - found_ids
            if missing:
                return _invalid(f"Question IDs not found: {sorted(missing)}")

        if category_id:
            # D2 "Category" filter. Report 9 #88: a main category covers the
            # questions in all of its subcategories, not only those filed
            # directly under it.
            category = space_filter(
                Category.objects.filter(id=category_id), self.request.user
            ).first()
            if category is None:
                return _invalid(f"Category {category_id} not found.")
            qs = qs.filter(category_id__in=_domain_category_ids(category))

        if question_ref:
            tokens = [t for t in question_ref.replace(",", " ").split() if t]
            ref_q = Q()
            for token in tokens:
                ref_q |= Q(question_id_label__iexact=token)
                if token.lstrip("#").isdigit():
                    ref_q |= Q(id=int(token.lstrip("#")))
            qs = qs.filter(ref_q)

        questions = list(qs.order_by("id"))

        date_from = data.get("date_from")
        date_to = data.get("date_to")
        assessment_id = data.get("assessment_id")
        region = (data.get("region") or "").strip() or None
        age_min = data.get("age_min")
        age_max = data.get("age_max")

        filters = {
            "date_from": _dt.fromisoformat(date_from) if date_from else None,
            "date_to": _dt.fromisoformat(date_to) if date_to else None,
            "assessment_id": assessment_id,
            "region": region,
            "age_min": int(age_min) if age_min not in (None, "") else None,
            "age_max": int(age_max) if age_max not in (None, "") else None,
        }
        return questions, filters, None

    @action(detail=False, methods=["post"], url_path="psychometric-extract")
    def psychometric_extract(self, request):
        """Extract step of psychometric analysis (Report 9 #87/#88, Doc 1
        §4.1.1: "User specifies filter criteria and clicks 'Extract' … System
        extracts questions … and lists them").

        Takes the same filter payload as psychometric_analysis, computes
        nothing and stores nothing: it lists the matching questions with the
        key facts the Psychometrician needs to choose which ones to analyse,
        including how many candidates' responses fall within the data
        filters (time period, assessment, region, age range).
        """
        from .psychometrics import extract_response_rows

        questions, filters, error = self._resolve_psychometric_filters(request.data)
        if error is not None:
            return error

        rows = []
        for q in questions:
            n = len(
                extract_response_rows(
                    q,
                    date_from=filters["date_from"],
                    date_to=filters["date_to"],
                    assessment_id=filters["assessment_id"],
                    region=filters["region"],
                    age_min=filters["age_min"],
                    age_max=filters["age_max"],
                )
            )
            rows.append(
                {
                    "id": q.id,
                    "question_id_label": q.question_id_label,
                    "question_title": q.question_title,
                    "question_type": q.question_type,
                    "question_type_label": q.get_question_type_display(),
                    "category_path": q.category.full_path if q.category_id else "",
                    "status": q.status,
                    "status_label": q.get_status_display(),
                    "is_active": q.is_active,
                    "difficulty_level": q.difficulty_level,
                    "n_candidates": n,
                    "item_difficulty_index": q.item_difficulty_index,
                    "discrimination_index": q.discrimination_index,
                    "item_total_correlation": q.item_total_correlation,
                    "psychometric_analyzed_at": q.psychometric_analyzed_at,
                }
            )

        return Response(
            {"message": f"Extracted {len(rows)} question(s).", "data": rows},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def psychometric_analysis(self, request):
        """Run psychometric analysis on one or more questions (SRS 02).

        Triggered by the Psychometrician. Computes per-question the analyses
        chosen in "analyses" (Doc 1 §4.1.1 "User selects relevant analyses";
        all three when omitted):
          - "difficulty": Item Difficulty Index (IDI, TDI, BDI, DDI)
          - "discrimination": Item Discrimination Index (MCQ questions)
          - "item_total": Item-Total Correlation Index (non-MCQ questions)

        Doc 1 §4.1.1: the outputs are only returned for inspection - nothing
        is stored here. When the Psychometrician clicks Submit the screen
        stores the inspected values through psychometric-upload/; Cancel
        simply discards them.

        Payload:
            {
                "question_ids": [1, 2, 3],         # required unless category_id given
                "category_id": 7,                  # optional (D2 "Category" filter) —
                                                     # auto-extracts all questions in the
                                                     # category (and its subcategories)
                                                     # when question_ids is omitted
                "question_ref": "12, QB-0007",     # optional Question ID filter (ids or
                                                     # display labels)
                "date_from": "2026-01-01",         # optional, ISO date
                "date_to": "2026-12-31",           # optional, ISO date
                "assessment_id": 42,               # optional, filter by assessment
                "region": "Karnataka",             # optional (D2 "Region" filter)
                "age_min": 18,                     # optional (D2 "User Age range" filter)
                "age_max": 30,                     # optional
                "analyses": ["difficulty", "discrimination", "item_total"]  # optional
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

        analyses = request.data.get("analyses")
        if analyses in (None, ""):
            analyses = list(PSYCHOMETRIC_ANALYSES)
        if (
            not isinstance(analyses, list)
            or not analyses
            or any(a not in PSYCHOMETRIC_ANALYSES for a in analyses)
        ):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "analyses must be a non-empty list of: "
                        + ", ".join(PSYCHOMETRIC_ANALYSES)
                        + ".",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        questions, filters, error = self._resolve_psychometric_filters(request.data)
        if error is not None:
            return error

        results = []
        for q in questions:
            r = run_psychometric_analysis(
                q,
                date_from=filters["date_from"],
                date_to=filters["date_to"],
                assessment_id=filters["assessment_id"],
                region=filters["region"],
                age_min=filters["age_min"],
                age_max=filters["age_max"],
                persist=False,
            )
            row = {
                "question_id": r.question_id,
                "n_candidates": r.n_candidates,
                "error": r.error,
            }
            # Only the chosen analyses are reported (null = not chosen).
            for analysis, fields in PSYCHOMETRIC_ANALYSES.items():
                for field in fields:
                    row[field] = getattr(r, field) if analysis in analyses else None
            results.append(row)

        return Response(
            {
                "message": f"Analysed {len(results)} question(s).",
                "data": results,
                "analyses": analyses,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="psychometric-data-download")
    def psychometric_data_download(self, request):
        """Manual analysis path, step 1 (D2 / SRS 02 "Manual Analysis" —
        "System displays option to download questions with user data").

        Accepts the same filter payload as psychometric_analysis (question_ids
        or category_id, date range, assessment, region, age range) and
        returns a CSV of the raw per-candidate response data extracted for
        each matched question, so the Psychometrician can compute indices
        offline and later re-upload them via psychometric-upload/.

        POST /api/question-bank/questions/psychometric-data-download/
          body: same shape as psychometric_analysis
        -> text/csv attachment with columns:
             question_id, candidate_id, session_id, target_score,
             target_max_score, total_score, rest_score, is_correct
        """
        from .psychometrics import extract_response_rows

        questions, filters, error = self._resolve_psychometric_filters(request.data)
        if error is not None:
            return error

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="psychometric_response_data.csv"'
        fieldnames = [
            "question_id",
            "candidate_id",
            "session_id",
            "target_score",
            "target_max_score",
            "total_score",
            "rest_score",
            "is_correct",
        ]
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        for q in questions:
            rows = extract_response_rows(
                q,
                date_from=filters["date_from"],
                date_to=filters["date_to"],
                assessment_id=filters["assessment_id"],
                region=filters["region"],
                age_min=filters["age_min"],
                age_max=filters["age_max"],
            )
            for row in rows:
                writer.writerow(row)

        return response

    @action(detail=False, methods=["post"], url_path="psychometric-upload")
    def psychometric_upload(self, request):
        """Manual analysis path, step 2 (D2 / SRS 02 "Manual Analysis" —
        "After performing analyses manually: User uploads output values or
        manually enters values. System stores output values against
        respective questions.").

        POST /api/question-bank/questions/psychometric-upload/
          body: {
            "results": [
              {
                "question_id": 1,
                "item_difficulty_index": 0.62,          # any subset of these
                "top_group_difficulty_index": 0.85,     # index fields may be
                "bottom_group_difficulty_index": 0.32,  # supplied — only the
                "difference_difficulty_index": 0.53,    # ones present are
                "discrimination_index": 0.41,           # written.
                "item_total_correlation": null
              },
              ...
            ]
          }

        Only the known index fields are accepted; unknown keys are ignored.
        Each row must include question_id and at least one index field.
        """
        results = request.data.get("results")
        if is_private_author(request.user):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Psychometric analysis is not available in your "
                        "organization's space.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not results or not isinstance(results, list):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "results (non-empty list) is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        index_fields = [
            "item_difficulty_index",
            "top_group_difficulty_index",
            "bottom_group_difficulty_index",
            "difference_difficulty_index",
            "discrimination_index",
            "item_total_correlation",
        ]

        updated = []
        errors = []
        for i, row in enumerate(results):
            if not isinstance(row, dict) or "question_id" not in row:
                errors.append({"index": i, "error": "question_id is required."})
                continue
            question = space_filter(
                Question.objects.filter(id=row["question_id"]), request.user
            ).first()
            if question is None:
                errors.append(
                    {"index": i, "question_id": row["question_id"], "error": "Not found."}
                )
                continue
            provided = [f for f in index_fields if f in row]
            if not provided:
                errors.append(
                    {
                        "index": i,
                        "question_id": question.id,
                        "error": "At least one index field is required.",
                    }
                )
                continue
            try:
                for field in provided:
                    value = row[field]
                    setattr(question, field, float(value) if value is not None else None)
            except (TypeError, ValueError):
                errors.append(
                    {
                        "index": i,
                        "question_id": question.id,
                        "error": "Index values must be numeric or null.",
                    }
                )
                continue
            question.psychometric_analyzed_at = timezone.now()
            question.save(update_fields=[*provided, "psychometric_analyzed_at"])
            updated.append(question.id)

        return Response(
            {
                "message": f"Updated {len(updated)} question(s), {len(errors)} error(s).",
                "data": {"updated_ids": updated, "errors": errors},
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
        question = get_object_or_404(
            space_filter(Question.objects.all(), request.user), id=question_id
        )

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

        # Report 9 #92: remember which psychometrician sent the question back,
        # so the SME's resubmission returns to him after content review.
        if review.action == "send_back" and review_type == "psychometric":
            question.assigned_psychometrician = request.user
            question.save(update_fields=["assigned_psychometrician", "updated_at"])

        # If content review approved, move to psychometric review
        if review.action == "approve" and review_type == "content":
            question.status = "pending_psychometric_review"
            update_fields = ["status", "updated_at"]
            # Report 9 #92: a resubmitted question goes back to the
            # psychometrician who sent it back, and he is told so.
            psychometrician = question.assigned_psychometrician
            if psychometrician is not None and not _usable_psychometrician(psychometrician):
                question.assigned_psychometrician = None
                update_fields.append("assigned_psychometrician")
                psychometrician = None
            question.save(update_fields=update_fields)
            if psychometrician is not None:
                try:
                    from apps.notifications.models import notify_user

                    notify_user(
                        psychometrician,
                        "Resubmitted question returned for psychometric review",
                        f"'{question.question_title}', which you sent back, has been "
                        "revised by the SME and cleared content review. It is back with "
                        "you for psychometric review.",
                        "review",
                        f"/question-bank/{question.id}?review=1",
                    )
                except Exception as e:  # pragma: no cover - notification is best-effort
                    logger.warning("Psychometrician notification failed: %s", e)

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
        question = get_object_or_404(
            space_filter(Question.objects.all(), request.user), id=question_id
        )
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
            {
                "message": "Request declined.",
                "data": QuestionBankDeletionRequestSerializer(dr).data,
            },
            status=status.HTTP_200_OK,
        )
