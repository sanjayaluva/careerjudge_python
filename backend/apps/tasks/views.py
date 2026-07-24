"""Views for the Task Management module.

Endpoints:
  GET/POST    /api/tasks/                              — list/create tasks (admin)
  GET/PATCH   /api/tasks/<id>/                         — retrieve/update task
  POST        /api/tasks/<id>/start/                   — assignee starts work
  POST        /api/tasks/<id>/submit/                  — assignee submits for review
  POST        /api/tasks/<id>/approve/                 — admin approves completion
  POST        /api/tasks/<id>/cancel/                  — admin cancels (with reason)
  POST        /api/tasks/<id>/request_update/          — admin requests progress update
  GET/POST    /api/tasks/<id>/progress/                — list/post progress updates
  GET/POST    /api/tasks/<id>/extensions/              — list/post extension requests
  POST        /api/tasks/extensions/<id>/approve/      — admin approves extension
  POST        /api/tasks/extensions/<id>/decline/      — admin declines extension
  GET         /api/tasks/my-tasks/                     — assignee's own tasks
  GET         /api/tasks/assigned/                     — admin's assigned tasks
"""

from django.db import models
from django.utils import timezone
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.notifications.models import notify_user

from .models import Task, TaskExtensionRequest, TaskProgressUpdate
from .serializers import (
    TaskDetailSerializer,
    TaskExtensionRequestSerializer,
    TaskListSerializer,
    TaskProgressUpdateSerializer,
)


def _is_admin(user) -> bool:
    if user.is_superuser:
        return True
    return user.role_id is not None and user.role.name == "cj_admin"


class TaskViewSet(ModelViewSet):
    """Task CRUD + lifecycle actions (start, submit, approve, cancel)."""

    queryset = Task.objects.select_related(
        "assigned_to", "assigned_by", "parent_task"
    ).prefetch_related("progress_updates", "extension_requests")
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["task_id", "title", "description", "assigned_to__email"]
    ordering_fields = ["created_at", "due_date", "status", "priority"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list":
            return TaskListSerializer
        return TaskDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_admin(user):
            return qs  # admin sees all tasks
        # Non-admins see only tasks assigned to them OR tasks they need to act on
        # (e.g. a reviewer may need to see a parent SME task)
        return qs.filter(models.Q(assigned_to=user) | models.Q(parent_task__assigned_to=user))

    def get_object_or_404(self, queryset, *args, **kwargs):
        """Override to allow non-admin assignees to retrieve by ID,
        but enforce action-level permission checks in the action methods."""
        obj = super().get_object_or_404(queryset, *args, **kwargs)
        return obj

    # ------------------------------------------------------------------
    # Lifecycle actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Assignee starts work — sets status to in_progress."""
        task = self.get_object()
        if task.assigned_to_id != request.user.id and not _is_admin(request.user):
            return Response(
                {"detail": "Only the assignee can start this task."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if task.status not in ("pending", "overdue"):
            return Response(
                {"detail": f"Cannot start task in status '{task.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = "in_progress"
        task.started_at = timezone.now()
        task.save()
        TaskProgressUpdate.objects.create(
            task=task,
            author=request.user,
            author_role="assignee",
            message="Task started.",
        )
        notify_user(
            task.assigned_by,
            f"Task started: {task.title}",
            f"{request.user.email} started task {task.task_id}.",
            "info",
            link=f"/tasks/{task.id}",
        )
        return Response(
            {"message": "Task started.", "data": TaskDetailSerializer(task).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Assignee submits task for admin review (mark work complete)."""
        task = self.get_object()
        if task.assigned_to_id != request.user.id:
            return Response(
                {"detail": "Only the assignee can submit this task."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if task.status not in ("in_progress", "overdue", "pending"):
            return Response(
                {"detail": f"Cannot submit task in status '{task.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message = request.data.get("message", "Task submitted for review.")
        task.status = "awaiting_review"
        task.save()
        TaskProgressUpdate.objects.create(
            task=task,
            author=request.user,
            author_role="assignee",
            message=message,
        )
        notify_user(
            task.assigned_by,
            f"Task submitted for review: {task.title}",
            f"{request.user.email} submitted task {task.task_id} for review.",
            "info",
            link=f"/tasks/{task.id}",
        )
        return Response(
            {"message": "Task submitted for review.", "data": TaskDetailSerializer(task).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Admin approves task completion — sets status to completed."""
        task = self.get_object()
        if not _is_admin(request.user):
            return Response(
                {"detail": "Only admin can approve task completion."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if task.status != "awaiting_review":
            return Response(
                {
                    "detail": f"Cannot approve task in status '{task.status}'. "
                    "Task must be awaiting review."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        comment = request.data.get("comment", "")
        task.status = "completed"
        task.approval_comment = comment
        task.completed_at = timezone.now()
        task.save()
        TaskProgressUpdate.objects.create(
            task=task,
            author=request.user,
            author_role="admin",
            message=f"Task approved. Comment: {comment}" if comment else "Task approved.",
        )
        notify_user(
            task.assigned_to,
            f"Task approved: {task.title}",
            f"Your task {task.task_id} has been approved by admin.",
            "success",
            link=f"/tasks/{task.id}",
        )
        return Response(
            {
                "message": "Task approved and marked complete.",
                "data": TaskDetailSerializer(task).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Admin cancels the task with a reason — assignee loses access."""
        task = self.get_object()
        if not _is_admin(request.user):
            return Response(
                {"detail": "Only admin can cancel tasks."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not task.can_be_cancelled:
            return Response(
                {"detail": f"Cannot cancel task in status '{task.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get("reason", "")
        if not reason:
            return Response(
                {"detail": "Cancellation reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = "cancelled"
        task.cancellation_reason = reason
        task.cancelled_at = timezone.now()
        task.save()
        TaskProgressUpdate.objects.create(
            task=task,
            author=request.user,
            author_role="admin",
            message=f"Task cancelled. Reason: {reason}",
        )
        notify_user(
            task.assigned_to,
            f"Task cancelled: {task.title}",
            f"Task {task.task_id} has been cancelled. Reason: {reason}",
            "warning",
            link=f"/tasks/{task.id}",
        )
        return Response(
            {"message": "Task cancelled.", "data": TaskDetailSerializer(task).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def request_update(self, request, pk=None):
        """Admin requests a progress update from assignee."""
        task = self.get_object()
        if not _is_admin(request.user):
            return Response(
                {"detail": "Only admin can request progress updates."},
                status=status.HTTP_403_FORBIDDEN,
            )
        message = request.data.get("message", "Please provide a progress update.")
        update = TaskProgressUpdate.objects.create(
            task=task,
            author=request.user,
            author_role="admin",
            message=message,
            is_admin_request=True,
        )
        notify_user(
            task.assigned_to,
            f"Progress update requested: {task.title}",
            f"Admin requested: {message}",
            "info",
            link=f"/tasks/{task.id}",
        )
        return Response(
            {
                "message": "Progress update requested.",
                "data": TaskProgressUpdateSerializer(update).data,
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # Progress + Extensions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get", "post"])
    def progress(self, request, pk=None):
        """List or post a progress update."""
        task = self.get_object()
        if request.method == "GET":
            updates = task.progress_updates.all()
            return Response(
                {
                    "message": "OK",
                    "data": TaskProgressUpdateSerializer(updates, many=True).data,
                }
            )
        # POST
        message = request.data.get("message", "")
        if not message:
            return Response(
                {"detail": "Message is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        author_role = "admin" if _is_admin(request.user) else "assignee"
        update = TaskProgressUpdate.objects.create(
            task=task,
            author=request.user,
            author_role=author_role,
            message=message,
        )
        # If assignee posted, notify admin. If admin posted, notify assignee.
        recipient = task.assigned_by if author_role == "assignee" else task.assigned_to
        notify_user(
            recipient,
            f"Progress update on: {task.title}",
            f"{request.user.email}: {message}",
            "info",
            link=f"/tasks/{task.id}",
        )
        return Response(
            {
                "message": "Progress update posted.",
                "data": TaskProgressUpdateSerializer(update).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def extensions(self, request, pk=None):
        """List or create extension requests."""
        task = self.get_object()
        if request.method == "GET":
            reqs = task.extension_requests.all()
            return Response(
                {
                    "message": "OK",
                    "data": TaskExtensionRequestSerializer(reqs, many=True).data,
                }
            )
        # POST — assignee requests extension
        if task.assigned_to_id != request.user.id and not _is_admin(request.user):
            return Response(
                {"detail": "Only the assignee can request an extension."},
                status=status.HTTP_403_FORBIDDEN,
            )
        requested_due_date = request.data.get("requested_due_date")
        reason = request.data.get("reason", "")
        if not requested_due_date:
            return Response(
                {"detail": "requested_due_date is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ext = TaskExtensionRequest.objects.create(
            task=task,
            requested_by=request.user,
            current_due_date=task.due_date,
            requested_due_date=requested_due_date,
            reason=reason,
        )
        notify_user(
            task.assigned_by,
            f"Extension requested: {task.title}",
            f"{request.user.email} requested extending {task.task_id} to {requested_due_date}.",
            "warning",
            link=f"/tasks/{task.id}",
        )
        return Response(
            {
                "message": "Extension request submitted.",
                "data": TaskExtensionRequestSerializer(ext).data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"])
    def my_tasks(self, request):
        """Tasks assigned to the current user (any role)."""
        qs = self.get_queryset().filter(assigned_to=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = TaskListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response({"message": "OK", "data": TaskListSerializer(qs, many=True).data})

    @action(detail=False, methods=["get"])
    def assigned(self, request):
        """Tasks assigned by the current admin."""
        if not _is_admin(request.user):
            return Response(
                {"detail": "Only admin can view assigned tasks."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = self.get_queryset().filter(assigned_by=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = TaskListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response({"message": "OK", "data": TaskListSerializer(qs, many=True).data})

    # ------------------------------------------------------------------
    # create() override — assignee must be a valid system role
    # ------------------------------------------------------------------

    def create(self, request, *args, **kwargs):
        if not _is_admin(request.user):
            return Response(
                {"detail": "Only admin can assign tasks."},
                status=status.HTTP_403_FORBIDDEN,
            )
        assigned_to_id = request.data.get("assigned_to")
        if not assigned_to_id:
            return Response(
                {"detail": "assigned_to (user ID) is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.accounts.models import User

        try:
            assignee = User.objects.get(pk=assigned_to_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Assigned user not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        assignee_role = request.data.get("assignee_role")
        if assignee_role not in dict(Task.ASSIGNEE_ROLE_CHOICES):
            return Response(
                {"detail": f"Invalid assignee_role '{assignee_role}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if assignee.role_id and assignee.role.name != assignee_role:
            return Response(
                {
                    "detail": f"User role mismatch. User has role "
                    f"'{assignee.role.name}', task requires '{assignee_role}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Inject assigned_by
        data = request.data.copy()
        data["assigned_by"] = request.user.id
        # Support optional parent_task lookup by task_id
        parent_task_id_str = data.get("parent_task_id")
        if parent_task_id_str:
            try:
                parent = Task.objects.get(task_id=parent_task_id_str)
                data["parent_task"] = parent.id
            except Task.DoesNotExist:
                return Response(
                    {"detail": f"Parent task '{parent_task_id_str}' not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"message": "Task created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        serializer.save()


class TaskExtensionViewSet(ModelViewSet):
    """Extension request approve/decline endpoints."""

    queryset = TaskExtensionRequest.objects.select_related("task", "requested_by", "reviewed_by")
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        if _is_admin(self.request.user):
            return qs
        return qs.filter(requested_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        ext = self.get_object()
        if not _is_admin(request.user):
            return Response(
                {"detail": "Only admin can approve extension requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if ext.status != "pending":
            return Response(
                {"detail": f"Cannot approve extension in status '{ext.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        comment = request.data.get("comment", "")
        ext.status = "approved"
        ext.reviewed_by = request.user
        ext.review_comment = comment
        ext.reviewed_at = timezone.now()
        ext.save()
        # Update task due date
        task = ext.task
        task.due_date = ext.requested_due_date
        if task.status == "overdue":
            task.status = "in_progress"
        task.save()
        notify_user(
            ext.requested_by,
            f"Extension approved: {task.title}",
            f"Extension for {task.task_id} approved. New due date: {ext.requested_due_date}.",
            "success",
            link=f"/tasks/{task.id}",
        )
        return Response(
            {
                "message": "Extension approved. Task due date updated.",
                "data": TaskExtensionRequestSerializer(ext).data,
            }
        )

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        ext = self.get_object()
        if not _is_admin(request.user):
            return Response(
                {"detail": "Only admin can decline extension requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if ext.status != "pending":
            return Response(
                {"detail": f"Cannot decline extension in status '{ext.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        comment = request.data.get("comment", "")
        ext.status = "declined"
        ext.reviewed_by = request.user
        ext.review_comment = comment
        ext.reviewed_at = timezone.now()
        ext.save()
        notify_user(
            ext.requested_by,
            f"Extension declined: {ext.task.title}",
            f"Extension for {ext.task.task_id} declined. Comment: {comment}",
            "warning",
            link=f"/tasks/{ext.task.id}",
        )
        return Response(
            {
                "message": "Extension declined.",
                "data": TaskExtensionRequestSerializer(ext).data,
            }
        )
