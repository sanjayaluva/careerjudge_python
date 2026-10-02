"""Training services shared by the learner's own registration and an
organization manager assigning a licensed course to his members
(Report 9 #15/#28/#59)."""

from django.utils import timezone

from .models import CourseRegistration


def assign_course_for_organization(course, student, organization, assigned_by):
    """Register ``student`` for ``course`` on his behalf, as assigned by his
    organization's manager. Returns ``(registration, created)``.

    The organization licensed the course from CJ Admin, so the member pays
    nothing: the registration is 'paid' at once and the payment record is a
    zero-amount 'free' one (no gateway step). The member is notified.
    """
    from apps.accounts.models import UserProfile
    from apps.notifications.models import notify_user
    from apps.payments.services import get_or_create_payment

    from .views import REGISTRATION_FORM_FIELDS

    existing = CourseRegistration.objects.filter(course=course, student=student).first()
    if existing is not None:
        return existing, False

    profile, _ = UserProfile.objects.get_or_create(user=student)
    registration_form = {
        "full_name": student.full_name,
        "email": student.email,
        **{f: getattr(profile, f, "") for f in REGISTRATION_FORM_FIELDS},
        "assigned_by_organization": organization.name,
    }
    reg = CourseRegistration.objects.create(
        course=course,
        student=student,
        payment_status="paid",
        completion_status="not_started",
        registration_form=registration_form,
        # Same as a free course: a scheduled course's countdown starts now.
        started_at=timezone.now() if course.schedule_type == "scheduled" else None,
        organization=organization,
        assigned_by=assigned_by,
    )
    get_or_create_payment(
        student,
        module="training",
        item_id=course.id,
        amount=0,
        description=f"Licensed by {organization.name}: {course.title}",
    )
    notify_user(
        student,
        f"Course assigned: {course.title}",
        f"{organization.name} has enrolled you in '{course.title}'. You can start it from "
        f"My Courses.",
        "info",
        f"/training/{course.id}",
    )
    return reg, True


def can_unassign(reg) -> bool:
    """A registration made by the organization can be withdrawn only until the
    learner starts the course."""
    return (
        reg.organization_id is not None
        and reg.completion_status == "not_started"
        and not reg.progress_records.exists()
    )


def unassign_course_for_organization(reg):
    """Withdraw a not-yet-started registration the organization made."""
    from apps.notifications.models import notify_user
    from apps.payments.models import Payment

    course, student = reg.course, reg.student
    org_name = reg.organization.name if reg.organization_id else "Your organization"
    reg.delete()
    # The zero-amount licence record goes with it, so a later self-registration
    # starts from a clean payment state.
    Payment.objects.filter(
        user=student, module="training", item_id=course.id, status="free"
    ).delete()
    notify_user(
        student,
        f"Course unassigned: {course.title}",
        f"{org_name} has withdrawn your enrolment in '{course.title}'.",
        "info",
        "/training",
    )


def registration_progress_rows(registrations) -> list[dict]:
    """Report 8.1 #62 (trainer) / Report 9 #17 (organization managers): each
    learner's course progress at a glance — status, completion %, items done
    of total, start, last activity, assessment and assignment scores — in one
    list instead of one ``progress_summary`` call per learner. The caller
    scopes ``registrations`` (the trainer's course, the manager's members)."""
    from apps.assessment.models import AssessmentSession

    from .models import AssignmentReport
    from .views import _course_completion, _sync_completion_status

    rows = []
    for reg in registrations:
        # Assessments complete outside the progress endpoint — re-sync first,
        # exactly as progress_summary does.
        _sync_completion_status(reg)
        records = list(reg.progress_records.all())
        pct, done, total = _course_completion(reg, records)
        last_activity = max(
            (p.last_accessed_at for p in records if p.last_accessed_at), default=None
        )
        assessment_scores = []
        for ca in reg.course.assessments.all():
            latest = (
                AssessmentSession.objects.filter(
                    assessment_id=ca.assessment_id, candidate=reg.student, status="completed"
                )
                .order_by("-completed_at")
                .first()
            )
            assessment_scores.append(
                {
                    "course_assessment_id": ca.id,
                    "title": ca.title,
                    "percentage": latest.percentage if latest else None,
                    "status": "completed" if latest else "not_attempted",
                }
            )
            if (
                latest
                and latest.completed_at
                and (last_activity is None or latest.completed_at > last_activity)
            ):
                last_activity = latest.completed_at
        assignment_reports = [
            {
                "report_id": ar.id,
                "assignment_id": ar.assignment_id,
                "assignment_title": ar.assignment.title,
                "status": ar.status,
                "trainer_score": ar.trainer_score,
                "submitted_at": ar.submitted_at.isoformat(),
            }
            for ar in AssignmentReport.objects.filter(
                assignment__session__topic__lesson__course=reg.course, student=reg.student
            ).select_related("assignment")
        ]
        last_activity = last_activity or reg.started_at
        rows.append(
            {
                "registration_id": reg.id,
                "course_id": reg.course_id,
                "user_id": reg.student_id,
                "full_name": reg.student.full_name,
                "email": reg.student.email,
                "payment_status": reg.payment_status,
                "completion_status": reg.completion_status,
                "completion_percentage": pct,
                "completed_count": done,
                "total_count": total,
                "registered_at": reg.registered_at.isoformat(),
                "started_at": reg.started_at.isoformat() if reg.started_at else None,
                "completed_at": reg.completed_at.isoformat() if reg.completed_at else None,
                "last_activity_at": last_activity.isoformat() if last_activity else None,
                "assessment_scores": assessment_scores,
                "assignment_reports": assignment_reports,
            }
        )
    return rows
