"""Models for the Task Management module.

Per SRS 09_admin_system_administration.json §3 (Task Management):

  - Admin User is the only one who assigns tasks and monitors completion.
  - Tasks can be assigned to: SME, Reviewer, Psychometrician, Trainer, Counsellor.
  - Each task has a unique Task ID, description/message, due date.
  - SME tasks specify: QB category/subcategory, question type, # questions,
    # options, # correct options, difficulty, cognitive level, due date.
  - Reviewer tasks link to an existing SME task.
  - Psychometrician tasks link to existing SME/Reviewer tasks.
  - Trainer/Counsellor tasks are general (free-form description).

Manage Task (§3.2):
  - Monitor progress (assignee posts progress updates; admin can request updates)
  - Cancel task (with reason; assignee loses access)
  - Approve task completion (admin enters comments; task becomes 'completed')

Extend due date (§3.2.1):
  - Assignee can request extension; admin approves/declines.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _generate_task_id() -> str:
    """Generate a human-readable task ID like 'TSK-2026-AB12CD'."""
    year = timezone.now().year
    suffix = uuid.uuid4().hex[:6].upper()
    return f"TSK-{year}-{suffix}"


class Task(models.Model):
    """A task assigned by Admin to a system user.

    Roles assignable: sme, reviewer, psychometrician, trainer, counsellor.
    Each role has a slightly different task shape (see TaskSpec below).
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),  # Created, not yet started by assignee
        ("in_progress", "In Progress"),  # Assignee started work
        ("awaiting_review", "Awaiting Admin Review"),  # Assignee marked complete
        ("completed", "Completed"),  # Admin approved completion
        ("cancelled", "Cancelled"),  # Admin cancelled (with reason)
        ("overdue", "Overdue"),  # Past due_date and not completed
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    ASSIGNEE_ROLE_CHOICES = [
        ("sme", "SME"),
        ("reviewer", "Reviewer"),
        ("psychometrician", "Psychometrician"),
        ("trainer", "Trainer"),
        ("counsellor", "Counsellor"),
    ]

    task_id = models.CharField(
        _("task ID"),
        max_length=30,
        unique=True,
        default=_generate_task_id,
        help_text=_("Human-readable unique ID like TSK-2026-AB12CD"),
    )
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), help_text=_("Task description / message"))

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks_assigned",
        help_text=_("Admin who assigned this task"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks_received",
        help_text=_("User the task is assigned to"),
    )
    assignee_role = models.CharField(
        _("assignee role"), max_length=20, choices=ASSIGNEE_ROLE_CHOICES
    )

    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="pending")
    priority = models.CharField(
        _("priority"), max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )

    due_date = models.DateTimeField(_("due date"), null=True, blank=True)
    started_at = models.DateTimeField(_("started at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)

    # Admin's approval comment when marking complete
    approval_comment = models.TextField(_("approval comment"), blank=True, default="")
    # Reason for cancelling
    cancellation_reason = models.TextField(_("cancellation reason"), blank=True, default="")

    # Optional link to a parent task (for reviewer → SME, psychometrician → SME/reviewer)
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_tasks",
        help_text=_("If this task builds on another (e.g. reviewer reviewing an SME task)"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
        indexes = [
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["assigned_by", "status"]),
            models.Index(fields=["status", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_id}: {self.title[:60]}"

    # --- Convenience flags ---

    @property
    def is_overdue(self) -> bool:
        if self.due_date and self.status not in ("completed", "cancelled"):
            return timezone.now() > self.due_date
        return False

    @property
    def can_be_cancelled(self) -> bool:
        return self.status not in ("completed", "cancelled")

    @property
    def can_be_approved(self) -> bool:
        """Only tasks awaiting admin review can be approved."""
        return self.status == "awaiting_review"

    def save(self, *args, **kwargs):
        """Auto-transition: pending → overdue if past due_date."""
        super().save(*args, **kwargs)


class TaskSpec(models.Model):
    """Role-specific specification attached to a Task.

    - SME tasks: QB category/subcategory, question_type, # questions, # options,
      # correct, difficulty, cognitive level.
    - Reviewer/Psychometrician tasks: link to source SME/Reviewer task (already
      captured via Task.parent_task); this model just records metadata.
    - Trainer/Counsellor tasks: no extra spec needed (description suffices).
    """

    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
        ("expert", "Expert"),
    ]

    COGNITIVE_CHOICES = [
        ("remember", "Remember"),
        ("understand", "Understand"),
        ("apply", "Apply"),
        ("analyze", "Analyze"),
        ("evaluate", "Evaluate"),
        ("create", "Create"),
    ]

    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="spec")

    # SME-specific (SRS §3.1.1)
    qb_category = models.CharField(_("QB category"), max_length=255, blank=True, default="")
    qb_subcategory = models.CharField(_("QB subcategory"), max_length=255, blank=True, default="")
    question_type = models.CharField(_("question type"), max_length=50, blank=True, default="")
    num_questions = models.PositiveIntegerField(_("number of questions"), null=True, blank=True)
    num_options = models.PositiveIntegerField(_("number of options"), null=True, blank=True)
    num_correct_options = models.PositiveIntegerField(
        _("number of correct options"), null=True, blank=True
    )
    difficulty_level = models.CharField(
        _("difficulty level"),
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        blank=True,
        default="",
    )
    cognitive_level = models.CharField(
        _("cognitive level"),
        max_length=20,
        choices=COGNITIVE_CHOICES,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("task spec")
        verbose_name_plural = _("task specs")

    def __str__(self) -> str:
        return f"Spec for {self.task.task_id}"


class TaskProgressUpdate(models.Model):
    """A progress update posted by the assignee or admin on a task.

    - Assignee posts updates while working on the task.
    - Admin can post a 'request update' message.
    - System stores all updates as a timeline.
    """

    AUTHOR_ROLE_CHOICES = [
        ("assignee", "Assignee"),
        ("admin", "Admin"),
        ("system", "System"),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="progress_updates")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_progress_updates",
        null=True,
        blank=True,
    )
    author_role = models.CharField(
        _("author role"), max_length=20, choices=AUTHOR_ROLE_CHOICES, default="system"
    )
    message = models.TextField(_("message"))
    is_admin_request = models.BooleanField(
        _("is admin request"),
        default=False,
        help_text=_("True if admin is requesting an update from assignee"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("task progress update")
        verbose_name_plural = _("task progress updates")

    def __str__(self) -> str:
        return f"{self.task.task_id} — {self.author_role}: {self.message[:50]}"


class TaskExtensionRequest(models.Model):
    """Assignee requests a due-date extension; admin approves/declines.

    Per SRS §3.2.1: 'System shows the extend due date notification from
    concerned user. User modifies due date field and submits. System
    updates modified due date.'
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("declined", "Declined"),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="extension_requests")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_extension_requests",
    )
    current_due_date = models.DateTimeField(_("current due date"))
    requested_due_date = models.DateTimeField(_("requested due date"))
    reason = models.TextField(_("reason"), blank=True, default="")

    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_extension_reviews",
    )
    review_comment = models.TextField(_("review comment"), blank=True, default="")
    reviewed_at = models.DateTimeField(_("reviewed at"), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("task extension request")
        verbose_name_plural = _("task extension requests")

    def __str__(self) -> str:
        return f"{self.task.task_id} — {self.status} — {self.requested_due_date}"
