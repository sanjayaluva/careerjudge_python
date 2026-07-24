"""Admin registration for the Task Management module."""

from django.contrib import admin

from .models import Task, TaskExtensionRequest, TaskProgressUpdate, TaskSpec


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "task_id",
        "title",
        "assigned_to",
        "assigned_by",
        "assignee_role",
        "status",
        "priority",
        "due_date",
        "is_overdue",
    )
    list_filter = ("status", "priority", "assignee_role")
    search_fields = ("task_id", "title", "description", "assigned_to__email")
    readonly_fields = (
        "task_id",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "cancelled_at",
    )


@admin.register(TaskSpec)
class TaskSpecAdmin(admin.ModelAdmin):
    list_display = ("task", "qb_category", "qb_subcategory", "question_type", "num_questions")
    search_fields = ("task__task_id", "qb_category", "qb_subcategory", "question_type")


@admin.register(TaskProgressUpdate)
class TaskProgressUpdateAdmin(admin.ModelAdmin):
    list_display = ("task", "author_role", "is_admin_request", "created_at")
    list_filter = ("author_role", "is_admin_request")
    search_fields = ("task__task_id", "message")


@admin.register(TaskExtensionRequest)
class TaskExtensionRequestAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "requested_by",
        "current_due_date",
        "requested_due_date",
        "status",
        "reviewed_by",
        "reviewed_at",
    )
    list_filter = ("status",)
    search_fields = ("task__task_id", "reason")
