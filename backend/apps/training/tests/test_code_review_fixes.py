"""Code review fixes (3 Oct 2026) — training: the editing window an approved
update request opens, registration scoping, archived courses, licensed
re-assignment, trainer notifications and the batched progress table.

Rights come from the real role table, exactly as in production.
"""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.notifications.models import Notification
from apps.organizations.models import Organization, OrganizationAssignment, OrganizationMember
from apps.training.models import (
    Assignment,
    CourseLesson,
    CourseModificationRequest,
    CourseProgress,
    CourseRegistration,
    LessonTopic,
    LiveSession,
    LiveSessionConsent,
    SessionContent,
    TopicSession,
    TrainingCourse,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _user(roles, role, email):
    return User.objects.create_user(
        email=email, password="pw", is_active=True, role=roles[role], full_name=email
    )


def _auth(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


@pytest.fixture
def people(roles):
    return {
        "admin": _user(roles, "cj_admin", "cja@test.com"),
        "trainer": _user(roles, "trainer", "trainer@test.com"),
        "other_trainer": _user(roles, "trainer", "other-trainer@test.com"),
        "learner": _user(roles, "individual", "learner@test.com"),
    }


def _course(created_by, status="published", **extra):
    course = TrainingCourse.objects.create(title="C", created_by=created_by, status=status, **extra)
    session = TopicSession.objects.create(
        topic=LessonTopic.objects.create(
            lesson=CourseLesson.objects.create(course=course, title="L"), title="T"
        ),
        title="S",
    )
    return course, session


def _approve(people, course):
    _auth(people["trainer"]).post(
        f"/api/training/courses/{course.id}/request-update/",
        {"request_type": "update", "reason": "fix content"},
        format="json",
    )
    cur = CourseModificationRequest.objects.get(course=course, status="pending")
    resp = _auth(people["admin"]).post(f"/api/training/course-update-requests/{cur.id}/approve/")
    assert resp.status_code == 200, resp.data
    cur.refresh_from_db()
    return cur


# --- #3: one approval opens an editing window --------------------------------


def test_approved_update_lets_the_trainer_edit_several_items(people):
    course, session = _course(people["trainer"])
    assignment = Assignment.objects.create(session=session, title="A1")
    cur = _approve(people, course)
    trainer = _auth(people["trainer"])

    resp = trainer.post(
        f"/api/training/sessions/{session.id}/contents/",
        {"title": "new video", "content_format": "text"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    resp = trainer.patch(
        f"/api/training/assignments/{assignment.id}/", {"title": "A1 fixed"}, format="json"
    )
    assert resp.status_code == 200, resp.data
    resp = trainer.patch(f"/api/training/courses/{course.id}/", {"title": "C2"}, format="json")
    assert resp.status_code == 200, resp.data
    assert trainer.get("/api/training/course-update-requests/").data["data"][0]["edit_window_open"]

    # "Finish editing" closes the window.
    resp = trainer.post(f"/api/training/course-update-requests/{cur.id}/finish-editing/")
    assert resp.status_code == 200, resp.data
    assert resp.data["data"]["edit_window_open"] is False
    resp = trainer.patch(
        f"/api/training/assignments/{assignment.id}/", {"title": "again"}, format="json"
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "approval_required"


def test_edit_window_closes_seven_days_after_approval(people):
    course, session = _course(people["trainer"])
    assignment = Assignment.objects.create(session=session, title="A1")
    cur = _approve(people, course)
    CourseModificationRequest.objects.filter(id=cur.id).update(
        reviewed_at=timezone.now() - timedelta(days=7, minutes=1)
    )
    resp = _auth(people["trainer"]).patch(
        f"/api/training/assignments/{assignment.id}/", {"title": "late"}, format="json"
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "approval_required"


def test_only_the_requesting_trainer_finishes_editing(people):
    course, _session = _course(people["trainer"])
    cur = _approve(people, course)
    resp = _auth(people["other_trainer"]).post(
        f"/api/training/course-update-requests/{cur.id}/finish-editing/"
    )
    assert resp.status_code in (403, 404)
    cur.refresh_from_db()
    assert cur.closed_at is None


# --- #8: registrations of a trainer's own courses only -----------------------


def test_trainer_cannot_reach_learners_of_a_course_he_does_not_run(people):
    course, _session = _course(people["trainer"])
    reg = CourseRegistration.objects.create(
        course=course, student=people["learner"], payment_status="paid"
    )
    other = _auth(people["other_trainer"])
    assert other.get(f"/api/training/registrations/{reg.id}/").status_code == 404
    assert other.get(f"/api/training/registrations/{reg.id}/progress_summary/").status_code == 404
    assert other.get(f"/api/training/registrations/{reg.id}/messages/").status_code == 404
    # The course's own trainer — and the trainer CJ Admin named on it — do.
    assert _auth(people["trainer"]).get(f"/api/training/registrations/{reg.id}/").status_code == 200
    course.trainer = people["other_trainer"]
    course.save()
    assert other.get(f"/api/training/registrations/{reg.id}/").status_code == 200


def test_exclusive_admin_follows_learners_of_his_private_course(roles, people):
    org = Organization.objects.create(name="Excl", type="corp_exclusive")
    excl_admin = _user(roles, "corp_exclusive", "excl@test.com")
    OrganizationMember.objects.create(organization=org, user=excl_admin, is_admin=True)
    member = _user(roles, "individual", "member@test.com")
    OrganizationMember.objects.create(organization=org, user=member)
    course, _session = _course(excl_admin, owner_organization=org)
    reg = CourseRegistration.objects.create(course=course, student=member, payment_status="paid")

    c = _auth(excl_admin)
    resp = c.get(f"/api/training/courses/{course.id}/registrations-progress/")
    assert resp.status_code == 200, resp.data
    assert [row["registration_id"] for row in resp.data["data"]] == [reg.id]
    assert c.get(f"/api/training/registrations/{reg.id}/progress_summary/").status_code == 200
    # CJ Admin still can't (Report 4 §3).
    cja = _auth(people["admin"])
    assert cja.get(f"/api/training/registrations/{reg.id}/").status_code == 404


# --- #9: a learner keeps his archived course ---------------------------------


def test_learner_keeps_access_to_an_archived_course_he_is_registered_in(people):
    course, _session = _course(people["trainer"])
    CourseRegistration.objects.create(
        course=course, student=people["learner"], payment_status="paid"
    )
    course.status = "archived"
    course.save()
    learner = _auth(people["learner"])
    assert learner.get(f"/api/training/courses/{course.id}/").status_code == 200
    # The catalogue still lists published courses only.
    listed = learner.get("/api/training/courses/").data["data"]
    rows = listed["results"] if isinstance(listed, dict) else listed
    assert course.id not in [row["id"] for row in rows]
    # Someone who never registered doesn't reach it.
    stranger = User.objects.create_user(
        email="s@test.com", password="pw", is_active=True, role=people["learner"].role
    )
    assert _auth(stranger).get(f"/api/training/courses/{course.id}/").status_code == 404


# --- #6: licensed assignment pays a pending self-registration ---------------


def test_assigning_a_licensed_course_pays_a_pending_self_registration(roles, people):
    from apps.payments.models import Payment
    from apps.training.services import assign_course_for_organization

    course, _session = _course(people["trainer"], price=100)
    learner = people["learner"]
    reg = CourseRegistration.objects.create(
        course=course, student=learner, payment_status="pending"
    )
    Payment.objects.create(
        user=learner, module="training", item_id=course.id, amount=100, status="pending"
    )
    org = Organization.objects.create(name="Acme", type="corporate")
    OrganizationMember.objects.create(organization=org, user=learner)
    OrganizationAssignment.objects.create(
        organization=org, item_type="training_course", item_id=course.id
    )
    manager = _user(roles, "corp_admin", "mgr@test.com")

    reg2, assigned = assign_course_for_organization(course, learner, org, manager)
    assert assigned and reg2.id == reg.id
    reg.refresh_from_db()
    assert reg.payment_status == "paid"
    assert reg.organization_id == org.id and reg.assigned_by_id == manager.id
    payment = Payment.objects.get(user=learner, module="training", item_id=course.id)
    assert payment.status == "free" and payment.amount == 0
    resp = _auth(learner).post(f"/api/training/registrations/{reg.id}/start/")
    assert resp.status_code == 200, resp.data


def test_manager_registers_for_a_licensed_course_free(roles, people):
    """The licence unlock follows the same members + managers predicate as
    course visibility: a manager who sees a licensed priced course is not
    sent to payment."""
    from apps.accounts.models import UserProfile
    from apps.training.tests.test_training import REGISTRATION_FORM

    org = Organization.objects.create(name="Excl", type="corp_exclusive")
    manager = _user(roles, "corp_exclusive", "excl@test.com")
    OrganizationMember.objects.create(organization=org, user=manager, is_admin=True)
    UserProfile.objects.update_or_create(user=manager, defaults=REGISTRATION_FORM)
    course, _session = _course(people["trainer"], price=100)
    OrganizationAssignment.objects.create(
        organization=org, item_type="training_course", item_id=course.id
    )
    resp = _auth(manager).post(f"/api/training/courses/{course.id}/register/", {}, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["payment_status"] == "paid"


# --- #7: the named trainer hears about his course ---------------------------


def _notified(user, text):
    return Notification.objects.filter(recipient=user, title__icontains=text).exists()


def test_named_trainer_is_notified_like_the_creator(people):
    from apps.payments.models import Payment
    from apps.payments.services import _update_module_payment_status

    course, _session = _course(people["admin"], trainer=people["trainer"], price=50)
    learner = people["learner"]
    reg = CourseRegistration.objects.create(
        course=course, student=learner, payment_status="pending"
    )

    resp = _auth(learner).post(
        "/api/training/live-session-requests/", {"course": course.id, "note": "pls"}
    )
    assert resp.status_code == 201, resp.data
    assert _notified(people["trainer"], "Live-session request")
    assert _notified(people["admin"], "Live-session request")

    live = LiveSession.objects.create(
        course=course,
        title="Q&A",
        scheduled_at=timezone.now() + timedelta(days=2),
        duration_minutes=60,
    )
    LiveSessionConsent.objects.create(live_session=live, student=learner, status="consented")
    assert _notified(people["trainer"], "consented to attend")

    payment = Payment.objects.create(
        user=learner, module="training", item_id=course.id, amount=50, status="paid"
    )
    _update_module_payment_status(payment)
    reg.refresh_from_db()
    assert reg.payment_status == "paid"
    assert _notified(people["trainer"], "Payment confirmed")


# --- #11: the progress table loads in a fixed number of queries -------------


def _learners_with_progress(roles, course, contents, n, start=0):
    for i in range(start, start + n):
        learner = _user(roles, "individual", f"l{i}@test.com")
        reg = CourseRegistration.objects.create(
            course=course, student=learner, payment_status="paid"
        )
        CourseProgress.objects.create(
            registration=reg,
            content_type="session_content",
            content_id=contents[0].id,
            is_completed=True,
        )


def test_registrations_progress_queries_do_not_grow_with_learners(roles, people):
    course, session = _course(people["trainer"])
    contents = [
        SessionContent.objects.create(
            session=session, title=f"c{i}", content_format="text", order=i
        )
        for i in range(2)
    ]
    trainer = _auth(people["trainer"])
    url = f"/api/training/courses/{course.id}/registrations-progress/"

    _learners_with_progress(roles, course, contents, 1)
    trainer.get(url)  # first read syncs the statuses
    with CaptureQueriesContext(connection) as one:
        resp = trainer.get(url)
    assert resp.status_code == 200

    _learners_with_progress(roles, course, contents, 5, start=1)
    trainer.get(url)
    with CaptureQueriesContext(connection) as six:
        resp = trainer.get(url)
    assert len(resp.data["data"]) == 6
    assert len(six.captured_queries) == len(one.captured_queries)
    # Once in step, reading the table writes nothing.
    assert not [q for q in six.captured_queries if q["sql"].lstrip().upper().startswith("UPDATE")]
    assert {row["completion_status"] for row in resp.data["data"]} == {"in_progress"}
    assert {row["completion_percentage"] for row in resp.data["data"]} == {50.0}
