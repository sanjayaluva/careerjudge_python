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
