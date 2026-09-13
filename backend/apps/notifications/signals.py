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


def _notify_admin_and_helpdesk(title, message, ntype="info", link=""):
    """Notify both cj_admin and helpdesk roles."""
    from .models import notify_role

    notify_role("cj_admin", title, message, ntype, link)
    notify_role("helpdesk", title, message, ntype, link)


# ---------------------------------------------------------------------------
# Doc 3 — Training + Counselling notification signals
# ---------------------------------------------------------------------------


@receiver(post_save, sender="training.CourseRegistration")
def notify_on_course_registration(sender, instance, created, **kwargs):
    """Per Doc 3 Issues 1.2, 1.5: notify admin + trainer on registration."""
    if not created:
        return
    from .models import notify_user

    course = instance.course
    # Notify admin
    _notify_admin_and_helpdesk(
        "New course registration",
        f"User {instance.student.email} registered for course '{course.title}'. Payment status: {instance.payment_status}.",
        "info",
        f"/training/{course.id}",
    )
    # Notify trainer
    if course.created_by:
        notify_user(
            course.created_by,
            "New course registration",
            f"User {instance.student.email} registered for your course '{course.title}'.",
            "info",
            f"/training/{course.id}",
        )


@receiver(post_save, sender="training.AssignmentReport")
def notify_on_assignment_report_submitted(sender, instance, created, **kwargs):
    """Per Doc 3 Issue 3.8: notify trainer when student submits report."""
    if not created:
        return
    from .models import notify_user

    assignment = instance.assignment
    trainer = assignment.session.topic.lesson.course.created_by
    if trainer:
        notify_user(
            trainer,
            "Assignment report submitted",
            f"Student {instance.student.email} submitted a report for '{assignment.title}'.",
            "info",
            f"/training/{assignment.session.topic.lesson.course.id}",
        )


@receiver(post_save, sender="training.CourseModificationRequest")
def notify_on_course_modification_request(sender, instance, created, **kwargs):
    """Per Doc 3 Issues 6.1, 6.2: notify admin on request, notify trainer on decision."""
    from .models import notify_user

    if created:
        # Notify admin of new request
        _notify_admin_and_helpdesk(
            f"Course {instance.request_type} request",
            f"Trainer {instance.trainer.email} requests to {instance.request_type} course '{instance.course.title}'. Reason: {instance.reason}",
            "warning",
            f"/training/{instance.course.id}",
        )
    elif instance.status in ("approved", "rejected"):
        # Notify trainer of decision
        notify_user(
            instance.trainer,
            f"Course {instance.request_type} {instance.status}",
            f"Your request to {instance.request_type} course '{instance.course.title}' was {instance.status}.",
            "success" if instance.status == "approved" else "warning",
            f"/training/{instance.course.id}",
        )


@receiver(post_save, sender="training.SessionReschedule")
def notify_on_session_reschedule(sender, instance, created, **kwargs):
    """Per Doc 3 Issue 6.6: notify registered users of reschedule."""
    if not created:
        return
    from apps.training.models import CourseRegistration

    from .models import notify_user

    course = instance.live_session.course
    # Notify all registered users
    for reg in CourseRegistration.objects.filter(course=course, status="active"):
        notify_user(
            reg.user,
            "Live session rescheduled",
            f"Session '{instance.live_session.title}' has been rescheduled to {instance.new_start_time}. Reason: {instance.reason}",
            "warning",
            f"/training/{course.id}",
        )


# ---------------------------------------------------------------------------
# D1 §2.2/§4.3 — Question Bank deletion-request workflow
# ---------------------------------------------------------------------------


@receiver(post_save, sender="question_bank.QuestionBankDeletionRequest")
def notify_on_qb_deletion_request(sender, instance, created, **kwargs):
    """Per D1 §2.2/§4.3: notify admin on new request, notify requester on decision."""
    from .models import notify_user

    if created:
        _notify_admin_and_helpdesk(
            f"{instance.target_type.capitalize()} deletion request",
            f"{instance.requester.email} requests to delete {instance.target_type} "
            f"'{instance.target_label}'. Reason: {instance.reason}",
            "warning",
            "/question-bank",
        )
    elif instance.status in ("approved", "rejected"):
        notify_user(
            instance.requester,
            f"Deletion request {instance.status}: {instance.target_label}",
            f"Your request to delete {instance.target_type} '{instance.target_label}' "
            f"was {instance.status}.",
            "success" if instance.status == "approved" else "warning",
            "/question-bank",
        )


# ---------------------------------------------------------------------------
# SRS 03_assessment_configuration.json §2.2/§2.3 — Assessment modification
# request workflow (title edit / delete on a published assessment)
# ---------------------------------------------------------------------------


@receiver(post_save, sender="assessment.AssessmentModificationRequest")
def notify_on_assessment_modification_request(sender, instance, created, **kwargs):
    """Notify admin on new request, notify requester on decision."""
    from .models import notify_user

    if created:
        _notify_admin_and_helpdesk(
            f"Assessment {instance.action} request",
            f"{instance.requester.email} requests to {instance.action} published assessment "
            f"'{instance.assessment.title}'. Reason: {instance.reason}",
            "warning",
            f"/assessments/{instance.assessment_id}",
        )
    elif instance.status in ("approved", "rejected"):
        notify_user(
            instance.requester,
            f"Assessment {instance.action} {instance.status}",
            f"Your request to {instance.action} '{instance.assessment.title}' was {instance.status}.",
            "success" if instance.status == "approved" else "warning",
            f"/assessments/{instance.assessment_id}",
        )
