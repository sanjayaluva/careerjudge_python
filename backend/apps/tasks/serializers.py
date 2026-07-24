"""Serializers for the Task Management module."""

from rest_framework import serializers

from apps.notifications.models import notify_user

from .models import Task, TaskExtensionRequest, TaskProgressUpdate, TaskSpec


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
    spec = TaskSpecSerializer(required=False)
    progress_updates = TaskProgressUpdateSerializer(many=True, read_only=True)
    extension_requests = TaskExtensionRequestSerializer(many=True, read_only=True)
    parent_task_id = serializers.CharField(source="parent_task.task_id", read_only=True)

    class Meta(TaskListSerializer.Meta):
        fields = [
            *TaskListSerializer.Meta.fields,
            "spec",
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

    def create(self, validated_data):
        spec_data = validated_data.pop("spec", None)
        task = Task.objects.create(**validated_data)
        if spec_data:
            TaskSpec.objects.create(task=task, **spec_data)
        # Notify the assignee
        notify_user(
            task.assigned_to,
            f"New task assigned: {task.title}",
            f"Task {task.task_id} has been assigned to you. Due: {task.due_date or 'No due date'}.",
            "info",
            link=f"/tasks/{task.id}",
        )
        return task

    def update(self, instance, validated_data):
        spec_data = validated_data.pop("spec", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if spec_data:
            spec, _ = TaskSpec.objects.get_or_create(task=instance)
            for attr, value in spec_data.items():
                setattr(spec, attr, value)
            spec.save()
        return instance
