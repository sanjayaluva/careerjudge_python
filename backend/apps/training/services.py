"""Training services shared by the learner's own registration and an
organization manager assigning a licensed course to his members
(Report 9 #15/#28/#59)."""

from django.utils import timezone

from .models import CourseRegistration


def is_course_unlocked(user, course) -> bool:
    """Is ``course`` paid for by ``user``'s organization? Report 9 #14/#52:
    CJ Admin licensed it to his organization — for members and managers
    alike, the same predicate that decides which CJ courses they see (code
    review: managers saw licensed priced courses but had to pay) — or it is
    his exclusive organization's own private course."""
    from apps.organizations.private_content import member_exclusive_org_ids
    from apps.organizations.scoping import assigned_item_ids, is_licence_scoped

    if course.owner_organization_id is not None:
        return course.owner_organization_id in member_exclusive_org_ids(user)
    return is_licence_scoped(user) and course.id in assigned_item_ids(user, "training_course")


def assign_course_for_organization(course, student, organization, assigned_by):
    """Register ``student`` for ``course`` on his behalf, as assigned by his
    organization's manager. Returns ``(registration, created)``.

    The organization licensed the course from CJ Admin, so the member pays
    nothing: the registration is 'paid' at once and the payment record is a
    zero-amount 'free' one (no gateway step). The member is notified.
    """
    from apps.accounts.models import UserProfile
    from apps.payments.services import get_or_create_payment

    from .views import REGISTRATION_FORM_FIELDS

    existing = CourseRegistration.objects.filter(course=course, student=student).first()
    if existing is not None and existing.payment_status == "paid":
        return existing, False
    if existing is not None:
        # Code review: the member self-registered (payment pending) before
        # the course was licensed — the organization's licence now pays, so
        # he can start it.
        from apps.payments.models import Payment

        existing.payment_status = "paid"
        existing.organization = organization
        existing.assigned_by = assigned_by
        if course.schedule_type == "scheduled" and not existing.started_at:
            existing.started_at = timezone.now()
        existing.save(update_fields=["payment_status", "organization", "assigned_by", "started_at"])
        Payment.objects.filter(
            user=student, module="training", item_id=course.id, status__in=("pending", "failed")
        ).update(
            amount=0,
            status="free",
            description=f"Licensed by {organization.name}: {course.title}",
        )
        _notify_assigned(student, course, organization)
        return existing, True

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
    _notify_assigned(student, course, organization)
    return reg, True


def _notify_assigned(student, course, organization):
    from apps.notifications.models import notify_user

    notify_user(
        student,
        f"Course assigned: {course.title}",
        f"{organization.name} has enrolled you in '{course.title}'. You can start it from "
        f"My Courses.",
        "info",
        f"/training/{course.id}",
    )


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
    scopes ``registrations`` (the trainer's course, the manager's members).

    Code review: everything is loaded in a fixed number of queries (not a few
    per learner), and a status that drifted from the progress (assessments
    complete outside the progress endpoint) is saved in one bulk update — on
    most reads there is nothing to save."""
    from collections import defaultdict

    from django.db.models import F

    from apps.assessment.models import AssessmentSession

    from .models import (
        AssignmentReport,
        CourseAssessment,
        CourseCompletionParameter,
        SessionContent,
    )
    from .views import _apply_completion_status

    regs = list(registrations)
    if not regs:
        return []
    course_ids = {reg.course_id for reg in regs}
    student_ids = {reg.student_id for reg in regs}

    assessments_by_course = defaultdict(list)
    for ca in CourseAssessment.objects.filter(course_id__in=course_ids):
        assessments_by_course[ca.course_id].append(ca)
    mandatory_by_course = defaultdict(list)
    for mp in CourseCompletionParameter.objects.filter(course_id__in=course_ids, is_mandatory=True):
        mandatory_by_course[mp.course_id].append((mp.content_type, mp.content_id))
    contents_by_course = defaultdict(list)
    for course_id, content_id in SessionContent.objects.filter(
        session__topic__lesson__course_id__in=course_ids
    ).values_list("session__topic__lesson__course_id", "id"):
        contents_by_course[course_id].append(("session_content", content_id))

    # Latest completed session per (candidate, assessment).
    latest_session = {}
    assessment_ids = {ca.assessment_id for cas in assessments_by_course.values() for ca in cas}
    for s in AssessmentSession.objects.filter(
        candidate_id__in=student_ids, assessment_id__in=assessment_ids, status="completed"
    ).order_by(F("completed_at").asc(nulls_first=True), "id"):
        latest_session[(s.candidate_id, s.assessment_id)] = s

    reports_by_reg = defaultdict(list)
    for ar in (
        AssignmentReport.objects.filter(
            assignment__session__topic__lesson__course_id__in=course_ids,
            student_id__in=student_ids,
        )
        .select_related("assignment")
        .annotate(report_course_id=F("assignment__session__topic__lesson__course_id"))
    ):
        reports_by_reg[(ar.report_course_id, ar.student_id)].append(ar)

    rows, changed, changed_fields = [], [], set()
    for reg in regs:
        records = list(reg.progress_records.all())
        course_assessments = assessments_by_course[reg.course_id]
        # Same rules as views._course_completion: done = completed progress
        # records + course assessments with a completed session; measured
        # against the mandatory parameters, else every session content.
        done_keys = {(p.content_type, p.content_id) for p in records if p.is_completed}
        for ca in course_assessments:
            if (reg.student_id, ca.assessment_id) in latest_session:
                done_keys.add(("assessment", ca.id))
        required = mandatory_by_course[reg.course_id] or contents_by_course[reg.course_id]
        total = len(required)
        done = sum(1 for key in required if key in done_keys)
        pct = round(done / total * 100, 1) if total else 0.0
        fields = _apply_completion_status(reg, bool(records), pct, total)
        if fields:
            changed.append(reg)
            changed_fields.update(fields)

        last_activity = max(
            (p.last_accessed_at for p in records if p.last_accessed_at), default=None
        )
        assessment_scores = []
        for ca in course_assessments:
            latest = latest_session.get((reg.student_id, ca.assessment_id))
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
            for ar in reports_by_reg[(reg.course_id, reg.student_id)]
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
    if changed:
        CourseRegistration.objects.bulk_update(changed, sorted(changed_fields))
    return rows
