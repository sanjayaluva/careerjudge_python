"""Serializers for the Task Management module."""

from rest_framework import serializers

from apps.notifications.models import notify_user
from apps.notifications.signals import _notify_admin_and_helpdesk

from .models import Concern, Task, TaskExtensionRequest, TaskProgressUpdate, TaskSpec


class TaskSpecSerializer(serializers.ModelSerializer):
    """Serializer for the SME-specific spec fields."""

    class Meta:
        model = TaskSpec
        fields = [
            "qb_category",
            "qb_subcategory",
            "question_type",
            "num_questions",
            "num_options",
            "num_correct_options",
            "difficulty_level",
            "cognitive_level",
        ]


class TaskProgressUpdateSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskProgressUpdate
        fields = [
            "id",
            "task",
            "author",
            "author_name",
            "author_role",
            "message",
            "is_admin_request",
            "created_at",
        ]
        read_only_fields = ["id", "task", "author", "author_role", "created_at"]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.full_name or obj.author.email
        return obj.author_role.title()


class TaskExtensionRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskExtensionRequest
        fields = [
            "id",
            "task",
            "requested_by",
            "requested_by_name",
            "current_due_date",
            "requested_due_date",
            "reason",
            "status",
            "reviewed_by",
            "review_comment",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "task",
            "requested_by",
            "current_due_date",
            "status",
            "reviewed_by",
            "reviewed_at",
            "created_at",
        ]

    def get_requested_by_name(self, obj):
        return obj.requested_by.full_name or obj.requested_by.email


class TaskListSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "task_id",
            "title",
            "description",
            "assigned_by",
            "assigned_by_name",
            "assigned_to",
            "assigned_to_name",
            "assignee_role",
            "status",
            "priority",
            "due_date",
            "is_overdue",
            "created_at",
            "completed_at",
            "cancelled_at",
        ]
        read_only_fields = ["task_id", "is_overdue", "created_at"]

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name or obj.assigned_to.email

    def get_assigned_by_name(self, obj):
        return obj.assigned_by.full_name or obj.assigned_by.email


class TaskDetailSerializer(TaskListSerializer):
    # `spec` is a write-only, single-row convenience — most SME tasks only
    # ever need one category/difficulty/type combination. `specs` is the
    # full multi-row list (D9 gap: multi-category SME task sheet) and is
    # what create()/update() actually persist against; `spec` is normalized
    # into a one-item `specs` list when given. Reads expose BOTH: `specs`
    # (the full list) and `spec` (the first row, for single-row callers —
    # see to_representation below).
    spec = TaskSpecSerializer(required=False, write_only=True)
    specs = TaskSpecSerializer(many=True, required=False)
    progress_updates = TaskProgressUpdateSerializer(many=True, read_only=True)
    extension_requests = TaskExtensionRequestSerializer(many=True, read_only=True)
    parent_task_id = serializers.CharField(source="parent_task.task_id", read_only=True)

    class Meta(TaskListSerializer.Meta):
        fields = [
            *TaskListSerializer.Meta.fields,
            "spec",
            "specs",
            "progress_updates",
            "extension_requests",
            "parent_task",
            "parent_task_id",
            "started_at",
            "approval_comment",
            "cancellation_reason",
            "updated_at",
        ]
        read_only_fields = [
            *TaskListSerializer.Meta.read_only_fields,
            "started_at",
            "completed_at",
            "approval_comment",
            "cancellation_reason",
            "updated_at",
            "status",  # status is managed via lifecycle actions (start/submit/approve/cancel)
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rows = data.get("specs") or []
        data["spec"] = rows[0] if rows else None
        return data

    @staticmethod
    def _spec_rows(validated_data: dict) -> list[dict] | None:
        """Merge the `specs` (multi-row) and `spec` (single-row, legacy)
        inputs into one list of spec-row dicts. Returns None when neither
        was provided (i.e. "don't touch the spec rows")."""
        specs_data = validated_data.pop("specs", None)
        spec_data = validated_data.pop("spec", None)
        if specs_data is not None:
            return specs_data
        if spec_data:
            return [spec_data]
        return None

    def create(self, validated_data):
        spec_rows = self._spec_rows(validated_data)
        task = Task.objects.create(**validated_data)
        for row in spec_rows or []:
            TaskSpec.objects.create(task=task, **row)
        # Notify the assignee
        notify_user(
            task.assigned_to,
            f"New task assigned: {task.title}",
            f"Task {task.task_id} has been assigned to you. Due: {task.due_date or 'No due date'}.",
            "info",
            link=f"/tasks/{task.id}",
        )
        # Also notify admin + helpdesk (D9 §3.1)
        _notify_admin_and_helpdesk(
            f"Task assigned: {task.title}",
            f"Task {task.task_id} was assigned to {task.assigned_to.full_name or task.assigned_to.email}.",
            "info",
            f"/tasks/{task.id}",
        )
        return task

    def update(self, instance, validated_data):
        spec_rows = self._spec_rows(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if spec_rows is not None:
            # Replace-all semantics: simplest predictable behavior for an
            # edit that supplies spec rows (matches how the rest of the
            # write API treats nested collections here — no partial merge).
            instance.specs.all().delete()
            for row in spec_rows:
                TaskSpec.objects.create(task=instance, **row)
        return instance


class ConcernSerializer(serializers.ModelSerializer):
    """A user-raised concern — routed to cj_admin + helpdesk (D9)."""

    raised_by_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Concern
        fields = [
            "id",
            "raised_by",
            "raised_by_name",
            "subject",
            "message",
            "related_task",
            "status",
            "resolved_by",
            "resolved_by_name",
            "resolution_comment",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "raised_by",
            "status",
            "resolved_by",
            "resolution_comment",
            "resolved_at",
            "created_at",
            "updated_at",
        ]

    def get_raised_by_name(self, obj):
        return obj.raised_by.full_name or obj.raised_by.email

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            return obj.resolved_by.full_name or obj.resolved_by.email
        return None

    def create(self, validated_data):
        concern = Concern.objects.create(raised_by=self.context["request"].user, **validated_data)
        task_ref = f" (re: task {concern.related_task.task_id})" if concern.related_task_id else ""
        _notify_admin_and_helpdesk(
            f"Concern raised: {concern.subject}",
            f"{concern.raised_by.full_name or concern.raised_by.email} raised a concern{task_ref}: "
            f"{concern.message}",
            "warning",
            f"/tasks/concerns/{concern.id}",
        )
        return concern
