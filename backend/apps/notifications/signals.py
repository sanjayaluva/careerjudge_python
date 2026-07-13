"""Signal handlers for the Notifications module.

Wires up system events to notification creation:
  - Question submitted for review → notify reviewers
  - Question approved/rejected → notify the SME who created it
  - Assessment published → notify all candidates (individual role)
  - Session completed → notify the candidate + counsellors
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.question_bank.models import Question, QuestionReview


@receiver(post_save, sender=Question)
def notify_on_question_status_change(sender, instance, created, **kwargs):
    """Send notifications when a question's status changes."""
    if created:
        return  # Don't notify on initial creation

    from .models import notify_role, notify_user

    # Question submitted for review → notify reviewers
    if instance.status == "pending_content_review":
        notify_role(
            "reviewer",
            "Question pending review",
            f"'{instance.question_title}' is pending content review.",
            "review",
            f"/question-bank/{instance.id}?review=1",
        )

    # Question confirmed → notify the SME who created it
    elif instance.status == "confirmed" and instance.created_by:
        notify_user(
            instance.created_by,
            "Question confirmed",
            f"Your question '{instance.question_title}' has been confirmed and added to the question bank.",
            "success",
            f"/question-bank/{instance.id}",
        )

    # Question sent back → notify the SME
    elif instance.status == "sent_back" and instance.created_by:
        notify_user(
            instance.created_by,
            "Question sent back for revision",
            f"Your question '{instance.question_title}' was sent back. Please check the review comments.",
            "warning",
            f"/question-bank/{instance.id}",
        )

    # Question rejected → notify the SME
    elif instance.status == "rejected" and instance.created_by:
        notify_user(
            instance.created_by,
            "Question rejected",
            f"Your question '{instance.question_title}' was rejected. Please check the review comments.",
            "error",
            f"/question-bank/{instance.id}",
        )


@receiver(post_save, sender=QuestionReview)
def notify_on_review_action(sender, instance, created, **kwargs):
    """When a reviewer takes action, notify the question's creator."""
    if not created:
        return

    from .models import notify_user

    question = instance.question
    if not question.created_by:
        return

    action_label = instance.get_action_display()
    review_type_label = instance.get_review_type_display()

    notify_user(
        question.created_by,
        f"Question {action_label.lower()}",
        f"Your question '{question.question_title}' was {action_label.lower()} during {review_type_label.lower()} by {instance.reviewer.full_name or instance.reviewer.email}.",
        "info" if instance.action == "approve" else "warning",
        f"/question-bank/{question.id}",
    )
