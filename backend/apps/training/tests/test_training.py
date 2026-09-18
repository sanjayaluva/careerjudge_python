"""Tests for the Training module.

Covers:
  - Category CRUD (admin)
  - Course CRUD (trainer creates, admin deletes)
  - Course publish (draft -> published)
  - Student registration (published courses only, idempotent)
  - my_courses endpoint (student sees only own registrations)
  - Progress tracking (upsert)
  - Permission enforcement (non-admin can't delete course)
"""

from datetime import UTC

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.assessment.tests.factories import get_or_create_role
from apps.training.models import (
    CourseProgress,
    CourseRegistration,
    TrainingCategory,
    TrainingCourse,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def cj_admin_user(db, roles):
    role = roles["cj_admin"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="training", action=action)
    return UserFactory(role=role, email="admin@test.com")


@pytest.fixture
def trainer_user(db, roles):
    role = roles["trainer"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="training", action=action)
    return UserFactory(role=role, email="trainer@test.com")


@pytest.fixture
def individual_user(db, roles):
    role = roles["individual"]
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(role=role, module="training", action=action)
    return UserFactory(role=role, email="student@test.com")


@pytest.fixture
def admin_client(db, cj_admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(cj_admin_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def trainer_client(db, trainer_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(trainer_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def student_client(db, individual_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(individual_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# Category tests
# ---------------------------------------------------------------------------


def test_admin_can_create_category(admin_client):
    resp = admin_client.post(
        "/api/training/categories/",
        {"name": "IT Training", "description": "IT courses"},
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["name"] == "IT Training"


def test_list_categories(admin_client):
    TrainingCategory.objects.create(name="Soft Skills")
    TrainingCategory.objects.create(name="IT")
    resp = admin_client.get("/api/training/categories/")
    assert resp.status_code == 200
    # List endpoints are paginated — data may be a dict with 'results' or a list
    data = resp.data["data"]
    results = data["results"] if isinstance(data, dict) and "results" in data else data
    names = [c["name"] for c in results]
    assert names == ["IT", "Soft Skills"]


# ---------------------------------------------------------------------------
# Course CRUD tests
# ---------------------------------------------------------------------------


def test_trainer_can_create_course(trainer_client, trainer_user):
    resp = trainer_client.post(
        "/api/training/courses/",
        {
            "title": "Python 101",
            "objective": "Learn Python basics",
            "course_type": "online_standard",
            "schedule_type": "non_scheduled",
            "price": "99.99",
        },
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    course = TrainingCourse.objects.get(id=resp.data["data"]["id"])
    assert course.created_by == trainer_user
    assert course.status == "draft"


def test_non_admin_cannot_delete_course(trainer_client, trainer_user):
    """Per SRS §5: 'Deleting a course is the right of Admin only'."""
    course = TrainingCourse.objects.create(
        title="Test Course", created_by=trainer_user, status="draft"
    )
    resp = trainer_client.delete(f"/api/training/courses/{course.id}/")
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "forbidden"
    # Course still exists
    assert TrainingCourse.objects.filter(id=course.id).exists()


def test_admin_can_delete_course(admin_client, trainer_user):
    course = TrainingCourse.objects.create(
        title="Test Course", created_by=trainer_user, status="draft"
    )
    resp = admin_client.delete(f"/api/training/courses/{course.id}/")
    assert resp.status_code == 204
    assert not TrainingCourse.objects.filter(id=course.id).exists()


def test_publish_course(trainer_client, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    resp = trainer_client.post(f"/api/training/courses/{course.id}/publish/")
    assert resp.status_code == 200
    course.refresh_from_db()
    assert course.status == "published"


def test_publish_rejects_non_draft(trainer_client, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    resp = trainer_client.post(f"/api/training/courses/{course.id}/publish/")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


def test_student_can_register_for_published_course(student_client, individual_user, trainer_user):
    course = TrainingCourse.objects.create(
        title="C", created_by=trainer_user, status="published", price="99.99"
    )
    resp = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    reg = CourseRegistration.objects.get(course=course, student=individual_user)
    assert reg.payment_status == "pending"
    assert reg.completion_status == "not_started"


def test_student_cannot_register_for_draft_course(student_client, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    resp = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp.status_code == 403


def test_registration_is_idempotent(student_client, individual_user, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    resp1 = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp1.status_code == 201
    resp2 = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp2.status_code == 200
    assert "Already registered" in resp2.data["message"]
    assert CourseRegistration.objects.filter(course=course, student=individual_user).count() == 1


def test_scheduled_course_sets_started_at(student_client, individual_user, trainer_user):
    """Per SRS §6: 'If training course is scheduled, course duration
    starts from this time' (registration time)."""
    course = TrainingCourse.objects.create(
        title="C", created_by=trainer_user, status="published", schedule_type="scheduled"
    )
    resp = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp.status_code == 201
    reg = CourseRegistration.objects.get(course=course, student=individual_user)
    assert reg.started_at is not None


def test_non_scheduled_course_leaves_started_at_null(student_client, individual_user, trainer_user):
    course = TrainingCourse.objects.create(
        title="C", created_by=trainer_user, status="published", schedule_type="non_scheduled"
    )
    resp = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp.status_code == 201
    reg = CourseRegistration.objects.get(course=course, student=individual_user)
    assert reg.started_at is None


def test_registration_captures_registration_form_snapshot(
    student_client, individual_user, trainer_user
):
    """Report 3 §1.1: registration stores a form snapshot (profile-prefilled
    + extra answers)."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    resp = student_client.post(
        f"/api/training/courses/{course.id}/register/",
        {"extra_answers": {"goal": "career switch", "experience": "3 years"}},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    reg = CourseRegistration.objects.get(course=course, student=individual_user)
    assert reg.registration_form["email"] == individual_user.email
    assert reg.registration_form["full_name"] == individual_user.full_name
    assert reg.registration_form["extra_answers"]["goal"] == "career switch"


def test_registration_creates_payment_record(student_client, individual_user, trainer_user):
    """Report 3 §1.3: paid-course registration creates a Payment record."""
    from apps.payments.models import Payment

    course = TrainingCourse.objects.create(
        title="Paid", created_by=trainer_user, status="published", price="49.99"
    )
    resp = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp.status_code == 201
    assert Payment.objects.filter(
        user=individual_user, module="training", item_id=course.id
    ).exists()


def test_registration_notifies_trainer(student_client, individual_user, trainer_user):
    """Report 3 §1.2/§1.5: successful registration fires a notification to
    the course trainer."""
    from apps.notifications.models import Notification

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    student_client.post(f"/api/training/courses/{course.id}/register/")
    # The notifications signal (remote) notifies trainer + admin + helpdesk.
    assert Notification.objects.filter(recipient=trainer_user).exists()


def test_my_courses_returns_only_own_registrations(
    student_client, individual_user, trainer_user, db
):
    """Student sees only their own registrations, not other students'."""
    other_student = UserFactory(
        role=get_or_create_role("individual", is_system=True), email="other@test.com"
    )
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    CourseRegistration.objects.create(course=course, student=individual_user)
    CourseRegistration.objects.create(course=course, student=other_student)

    resp = student_client.get("/api/training/courses/my_courses/")
    assert resp.status_code == 200
    regs = resp.data["data"]
    assert len(regs) == 1
    assert regs[0]["student"] == individual_user.id


# ---------------------------------------------------------------------------
# Progress tracking tests
# ---------------------------------------------------------------------------


def test_progress_upsert(student_client, individual_user, trainer_user):
    """POST /registrations/<id>/progress/ creates then updates a record."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(course=course, student=individual_user)

    # First POST: create
    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/progress/",
        {
            "content_type": "session_content",
            "content_id": 42,
            "is_completed": False,
            "time_spent_seconds": 60,
        },
        format="json",
    )
    assert resp.status_code == 200
    assert CourseProgress.objects.filter(registration=reg).count() == 1
    progress = CourseProgress.objects.get(registration=reg)
    assert progress.is_completed is False
    assert progress.time_spent_seconds == 60
    assert progress.last_accessed_at is not None

    # Second POST: update (same content_type + content_id -> upsert)
    resp2 = student_client.post(
        f"/api/training/registrations/{reg.id}/progress/",
        {
            "content_type": "session_content",
            "content_id": 42,
            "is_completed": True,
            "time_spent_seconds": 120,
        },
        format="json",
    )
    assert resp2.status_code == 200
    assert CourseProgress.objects.filter(registration=reg).count() == 1  # still 1, not 2
    progress.refresh_from_db()
    assert progress.is_completed is True
    assert progress.time_spent_seconds == 120


def test_progress_list(student_client, individual_user, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    CourseProgress.objects.create(
        registration=reg, content_type="session_content", content_id=1, is_completed=True
    )
    CourseProgress.objects.create(
        registration=reg, content_type="assignment", content_id=2, is_completed=False
    )
    resp = student_client.get(f"/api/training/registrations/{reg.id}/progress/")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 2


# ---------------------------------------------------------------------------
# Course structure tests
# ---------------------------------------------------------------------------


def test_add_lesson_to_course(admin_client, trainer_user):
    """Per SRS §5: course structure modification is admin-only."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    resp = admin_client.post(
        f"/api/training/courses/{course.id}/lessons/",
        {"title": "Lesson 1", "week_number": 1, "order": 1},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["title"] == "Lesson 1"


def test_trainer_lesson_create_gated_like_other_structure(trainer_client, trainer_user):
    """TRN-7 / §5: lesson creation is gated the same as topic/session/content —
    a trainer may build a DRAFT course's structure, but a PUBLISHED course
    requires admin approval (uniform gating)."""
    draft = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    resp = trainer_client.post(
        f"/api/training/courses/{draft.id}/lessons/",
        {"title": "Lesson 1", "week_number": 1, "order": 1},
        format="json",
    )
    assert resp.status_code == 201, resp.data

    published = TrainingCourse.objects.create(
        title="P", created_by=trainer_user, status="published"
    )
    resp2 = trainer_client.post(
        f"/api/training/courses/{published.id}/lessons/",
        {"title": "Lesson 2", "week_number": 1, "order": 1},
        format="json",
    )
    assert resp2.status_code == 403


def test_add_live_session_to_course(trainer_client, trainer_user):
    from datetime import datetime, timedelta

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    scheduled = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    resp = trainer_client.post(
        f"/api/training/courses/{course.id}/live_sessions/",
        {
            "title": "Zoom Q&A",
            "mode": "online",
            "meeting_url": "https://zoom.us/j/123",
            "scheduled_at": scheduled,
            "duration_minutes": 60,
        },
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["mode"] == "online"


def test_course_detail_includes_nested_structure(trainer_client, trainer_user):
    """GET /courses/<id>/ returns the full nested structure:
    lessons -> topics -> sessions -> contents + assignments.
    """
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    resp = trainer_client.get(f"/api/training/courses/{course.id}/")
    assert resp.status_code == 200
    # Even with no children, the arrays should be present
    assert resp.data["data"]["lessons"] == []
    assert resp.data["data"]["live_sessions"] == []
    assert resp.data["data"]["assessments"] == []


def test_course_list_filters_by_status(trainer_client, trainer_user):
    TrainingCourse.objects.create(title="Draft 1", created_by=trainer_user, status="draft")
    TrainingCourse.objects.create(title="Pub 1", created_by=trainer_user, status="published")
    TrainingCourse.objects.create(title="Pub 2", created_by=trainer_user, status="published")

    resp = trainer_client.get("/api/training/courses/?status=published")
    assert resp.status_code == 200
    titles = [c["title"] for c in resp.data["data"]["results"]]
    assert titles == ["Pub 2", "Pub 1"]  # ordered by -created_at


def test_course_list_filters_by_category(trainer_client, trainer_user):
    cat1 = TrainingCategory.objects.create(name="IT")
    cat2 = TrainingCategory.objects.create(name="Soft Skills")
    TrainingCourse.objects.create(title="A", created_by=trainer_user, category=cat1)
    TrainingCourse.objects.create(title="B", created_by=trainer_user, category=cat2)

    resp = trainer_client.get(f"/api/training/courses/?category={cat1.id}")
    assert resp.status_code == 200
    titles = [c["title"] for c in resp.data["data"]["results"]]
    assert titles == ["A"]


# ---------------------------------------------------------------------------
# Assignment reports (SRS §2.3.2)
# ---------------------------------------------------------------------------


def test_student_submits_assignment_report(student_client, individual_user, trainer_user):
    """SRS §2.3.2: student submits report, trainer can view it."""
    from apps.training.models import Assignment, CourseLesson, LessonTopic, TopicSession

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T1", order=1)
    session = TopicSession.objects.create(topic=topic, title="S1", order=1)
    assignment = Assignment.objects.create(
        session=session,
        title="A1",
        report_submission_enabled=True,
        report_instructions="Write a summary",
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)

    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/assignment_reports/",
        {"assignment": assignment.id, "report_text": "My report content"},
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["status"] == "submitted"
    assert resp.data["data"]["report_text"] == "My report content"


def test_student_cannot_submit_report_for_disabled_assignment(
    student_client, individual_user, trainer_user
):
    """Report submission must be enabled on the assignment."""
    from apps.training.models import Assignment, CourseLesson, LessonTopic, TopicSession

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T1", order=1)
    session = TopicSession.objects.create(topic=topic, title="S1", order=1)
    assignment = Assignment.objects.create(
        session=session, title="A1", report_submission_enabled=False
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)

    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/assignment_reports/",
        {"assignment": assignment.id, "report_text": "content"},
        format="json",
    )
    assert resp.status_code == 400
    assert "not enabled" in resp.data["error"]["message"]


def test_trainer_reviews_report(trainer_client, trainer_user, individual_user):
    """SRS §2.3.2: trainer gives score + feedback on a submitted report."""
    from apps.training.models import (
        Assignment,
        AssignmentReport,
        CourseLesson,
        LessonTopic,
        TopicSession,
    )

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T1", order=1)
    session = TopicSession.objects.create(topic=topic, title="S1", order=1)
    assignment = Assignment.objects.create(
        session=session, title="A1", report_submission_enabled=True
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    report = AssignmentReport.objects.create(
        assignment=assignment, student=individual_user, report_text="content"
    )

    resp = trainer_client.post(
        f"/api/training/registrations/{reg.id}/review-report/",
        {"report_id": report.id, "trainer_score": 8.5, "trainer_feedback": "Good work"},
        format="json",
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    report.refresh_from_db()
    assert report.status == "reviewed"
    assert report.trainer_score == 8.5
    assert report.trainer_feedback == "Good work"
    assert report.reviewed_by == trainer_user
    assert report.reviewed_at is not None


def test_trainer_review_rejects_score_above_10(trainer_client, trainer_user, individual_user):
    """Report 3 §3.8: trainer rating is on a 0-10 scale."""
    from apps.training.models import (
        Assignment,
        AssignmentReport,
        CourseLesson,
        LessonTopic,
        TopicSession,
    )

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T1", order=1)
    session = TopicSession.objects.create(topic=topic, title="S1", order=1)
    assignment = Assignment.objects.create(
        session=session, title="A1", report_submission_enabled=True
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    report = AssignmentReport.objects.create(
        assignment=assignment, student=individual_user, report_text="content"
    )

    resp = trainer_client.post(
        f"/api/training/registrations/{reg.id}/review-report/",
        {"report_id": report.id, "trainer_score": 85},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["error"]["code"] == "validation_error"


def test_submission_after_deadline_requires_approval(
    trainer_client, trainer_user, student_client, individual_user
):
    """Report 3 §3.3: after the deadline, submission is blocked unless the
    trainer approves a late submission."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.training.models import (
        Assignment,
        CourseLesson,
        LessonTopic,
        TopicSession,
    )

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T1", order=1)
    session = TopicSession.objects.create(topic=topic, title="S1", order=1)
    # Deadline already passed
    assignment = Assignment.objects.create(
        session=session,
        title="A1",
        report_submission_enabled=True,
        submission_deadline=timezone.now() - timedelta(hours=1),
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)

    # 1) Student cannot submit after the deadline
    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/assignment_reports/",
        {"assignment": assignment.id, "report_text": "late"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "deadline_passed"

    # 2) Trainer approves late submission
    from apps.training.models import AssignmentReport

    report = AssignmentReport.objects.create(
        assignment=assignment, student=individual_user, report_text=""
    )
    resp = trainer_client.post(
        f"/api/training/registrations/{reg.id}/approve-late-submission/",
        {"report_id": report.id},
        format="json",
    )
    assert resp.status_code == 200

    # 3) Now the student can submit
    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/assignment_reports/",
        {"assignment": assignment.id, "report_text": "late content"},
        format="json",
    )
    assert resp.status_code in (200, 201), resp.data


def test_student_cannot_review_report(student_client, individual_user, trainer_user):
    """Only the trainer or admin can review reports."""
    from apps.training.models import (
        Assignment,
        AssignmentReport,
        CourseLesson,
        LessonTopic,
        TopicSession,
    )

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T1", order=1)
    session = TopicSession.objects.create(topic=topic, title="S1", order=1)
    assignment = Assignment.objects.create(
        session=session, title="A1", report_submission_enabled=True
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    report = AssignmentReport.objects.create(
        assignment=assignment, student=individual_user, report_text="content"
    )

    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/review-report/",
        {"report_id": report.id, "trainer_score": 100},
        format="json",
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Messaging (SRS §5)
# ---------------------------------------------------------------------------


def test_student_sends_message_to_trainer(student_client, individual_user, trainer_user):
    """SRS §5: student can message the trainer."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(course=course, student=individual_user)

    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/messages/",
        {"body": "I have a question about lesson 1"},
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["body"] == "I have a question about lesson 1"
    assert resp.data["data"]["sender"] == individual_user.id


def test_trainer_sends_message_to_student(trainer_client, trainer_user, individual_user):
    """SRS §5: trainer can respond to student messages."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(course=course, student=individual_user)

    resp = trainer_client.post(
        f"/api/training/registrations/{reg.id}/messages/",
        {"body": "Here's the answer"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["sender"] == trainer_user.id


def test_unauthorized_user_cannot_send_message(student_client, individual_user, trainer_user, db):
    """A user who is neither the student nor the trainer can't message."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.accounts.tests.factories import UserFactory
    from apps.assessment.tests.factories import get_or_create_role

    other_role = get_or_create_role("individual", is_system=True)
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(role=other_role, module="training", action=action)
    other_user = UserFactory(role=other_role, email="other@test.com")

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(course=course, student=individual_user)

    other_client = APIClient()
    refresh = RefreshToken.for_user(other_user)
    other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    resp = other_client.post(
        f"/api/training/registrations/{reg.id}/messages/",
        {"body": "intrusion attempt"},
        format="json",
    )
    # The other user can't even see the registration (get_queryset filters
    # to their own), so they get 404 — effectively denied access.
    assert resp.status_code in (403, 404)


def test_list_messages(student_client, individual_user, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    from apps.training.models import CourseMessage

    CourseMessage.objects.create(registration=reg, sender=individual_user, body="Q1")
    CourseMessage.objects.create(registration=reg, sender=trainer_user, body="A1")

    resp = student_client.get(f"/api/training/registrations/{reg.id}/messages/")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 2


# ---------------------------------------------------------------------------
# Progress summary (SRS §6)
# ---------------------------------------------------------------------------


def test_progress_summary_aggregates_completion(student_client, individual_user, trainer_user):
    """SRS §6: 'Course Completion Status, Time Tracker, Option to resume'."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    from apps.training.models import CourseProgress

    # 2 of 4 contents completed -> 50%
    CourseProgress.objects.create(
        registration=reg,
        content_type="session_content",
        content_id=1,
        is_completed=True,
        time_spent_seconds=60,
    )
    CourseProgress.objects.create(
        registration=reg,
        content_type="session_content",
        content_id=2,
        is_completed=True,
        time_spent_seconds=120,
    )
    CourseProgress.objects.create(
        registration=reg,
        content_type="assignment",
        content_id=3,
        is_completed=False,
        time_spent_seconds=30,
    )
    CourseProgress.objects.create(
        registration=reg,
        content_type="assignment",
        content_id=4,
        is_completed=False,
        time_spent_seconds=0,
    )

    resp = student_client.get(f"/api/training/registrations/{reg.id}/progress_summary/")
    assert resp.status_code == 200
    data = resp.data["data"]
    assert data["completion_percentage"] == 50.0
    assert data["completed_count"] == 2
    assert data["total_count"] == 4
    assert data["total_time_spent_seconds"] == 210  # 60+120+30+0
    assert data["last_content"] is not None  # resume point


def test_progress_summary_scheduled_course_has_time_left(
    student_client, individual_user, trainer_user
):
    """Scheduled courses compute time_left from duration_days - elapsed."""
    course = TrainingCourse.objects.create(
        title="C",
        created_by=trainer_user,
        status="published",
        schedule_type="scheduled",
        duration_days=30,
    )
    from django.utils import timezone

    started = timezone.now()
    reg = CourseRegistration.objects.create(
        course=course, student=individual_user, started_at=started
    )

    resp = student_client.get(f"/api/training/registrations/{reg.id}/progress_summary/")
    assert resp.status_code == 200
    data = resp.data["data"]
    assert data["total_time_allowed_seconds"] == 30 * 86400
    assert data["time_left_seconds"] is not None
    assert data["time_left_seconds"] > 0
    assert data["is_expired"] is False


def test_progress_summary_non_scheduled_no_time_limit(
    student_client, individual_user, trainer_user
):
    """Non-scheduled courses have no time limit."""
    course = TrainingCourse.objects.create(
        title="C", created_by=trainer_user, status="published", schedule_type="non_scheduled"
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)

    resp = student_client.get(f"/api/training/registrations/{reg.id}/progress_summary/")
    assert resp.status_code == 200
    data = resp.data["data"]
    assert data["total_time_allowed_seconds"] is None
    assert data["time_left_seconds"] is None
    assert data["is_expired"] is False


def test_free_course_auto_paid_on_register(student_client, individual_user, trainer_user):
    """Free courses (price=0) should auto-set payment_status='paid'."""
    course = TrainingCourse.objects.create(
        title="Free Course", created_by=trainer_user, status="published", price="0"
    )
    resp = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp.status_code == 201
    reg = CourseRegistration.objects.get(course=course, student=individual_user)
    assert reg.payment_status == "paid"
    assert reg.completion_status == "in_progress"


def test_paid_course_stays_pending(student_client, individual_user, trainer_user):
    """Paid courses (price>0) should stay payment_status='pending'."""
    course = TrainingCourse.objects.create(
        title="Paid Course", created_by=trainer_user, status="published", price="99.99"
    )
    resp = student_client.post(f"/api/training/courses/{course.id}/register/")
    assert resp.status_code == 201
    reg = CourseRegistration.objects.get(course=course, student=individual_user)
    assert reg.payment_status == "pending"
    assert reg.completion_status == "not_started"


# ---------------------------------------------------------------------------
# Course Update Request workflow (Report 3 §7.1/§7.2)
# ---------------------------------------------------------------------------


def test_trainer_can_request_course_update(trainer_client, trainer_user):
    """Report 3 §7.1: trainer requests admin approval to update a published course."""
    from apps.training.models import CourseModificationRequest

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    resp = trainer_client.post(
        f"/api/training/courses/{course.id}/request-update/",
        {"request_type": "update", "reason": "Fix lesson 2 typo"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    cur = CourseModificationRequest.objects.get(course=course)
    assert cur.request_type == "update"
    assert cur.status == "pending"
    assert cur.trainer == trainer_user


def test_non_trainer_cannot_request_update(student_client, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    resp = student_client.post(
        f"/api/training/courses/{course.id}/request-update/",
        {"request_type": "update", "reason": "x"},
        format="json",
    )
    assert resp.status_code == 403


def test_admin_approve_delete_archives_course(admin_client, trainer_client, trainer_user):
    """Report 3 §7.2: when admin approves a delete request, the course is archived."""
    from apps.training.models import CourseModificationRequest

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    trainer_client.post(
        f"/api/training/courses/{course.id}/request-update/",
        {"request_type": "delete", "reason": "Obsolete"},
        format="json",
    )
    cur = CourseModificationRequest.objects.get(course=course)
    resp = admin_client.post(
        f"/api/training/course-update-requests/{cur.id}/approve/",
        {"admin_note": "OK"},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    course.refresh_from_db()
    assert course.status == "archived"
    cur.refresh_from_db()
    assert cur.status == "approved"


def test_non_admin_cannot_approve_request(trainer_client, trainer_user):
    from apps.training.models import CourseModificationRequest

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    cur = CourseModificationRequest.objects.create(
        course=course, trainer=trainer_user, request_type="update", reason="x"
    )
    resp = trainer_client.post(
        f"/api/training/course-update-requests/{cur.id}/approve/",
        format="json",
    )
    assert resp.status_code == 403


def test_admin_decline_keeps_course_and_notifies(admin_client, trainer_client, trainer_user):
    from apps.notifications.models import Notification
    from apps.training.models import CourseModificationRequest

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    trainer_client.post(
        f"/api/training/courses/{course.id}/request-update/",
        {"request_type": "update", "reason": "x"},
        format="json",
    )
    cur = CourseModificationRequest.objects.get(course=course)
    admin_client.post(
        f"/api/training/course-update-requests/{cur.id}/decline/",
        {"admin_note": "Not now"},
        format="json",
    )
    course.refresh_from_db()
    assert course.status == "published"  # unchanged
    cur.refresh_from_db()
    assert cur.status == "rejected"
    assert Notification.objects.filter(recipient=trainer_user, title__contains="declined").exists()


# ---------------------------------------------------------------------------
# TRN-1 / Doc 7 §5 — nested structure edit/delete gated on published courses
# ---------------------------------------------------------------------------


def test_trainer_cannot_delete_published_lesson_directly(trainer_client, trainer_user):
    """TRN-1: a trainer cannot DELETE a published course's lesson directly —
    it must go through the request-update/approval flow (403)."""
    from apps.training.models import CourseLesson

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    resp = trainer_client.delete(f"/api/training/lessons/{lesson.id}/")
    assert resp.status_code == 403
    assert CourseLesson.objects.filter(id=lesson.id).exists()


def test_trainer_cannot_patch_published_lesson_directly(trainer_client, trainer_user):
    """TRN-1: a trainer cannot PATCH a published course's lesson directly (403)."""
    from apps.training.models import CourseLesson

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    resp = trainer_client.patch(
        f"/api/training/lessons/{lesson.id}/", {"title": "hacked"}, format="json"
    )
    assert resp.status_code == 403
    lesson.refresh_from_db()
    assert lesson.title == "L1"


def test_trainer_can_delete_draft_lesson(trainer_client, trainer_user):
    """TRN-1: gating only applies once published — draft structure is freely
    editable by the authoring trainer."""
    from apps.training.models import CourseLesson

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    resp = trainer_client.delete(f"/api/training/lessons/{lesson.id}/")
    assert resp.status_code in (200, 204)
    assert not CourseLesson.objects.filter(id=lesson.id).exists()


def test_admin_can_delete_published_lesson_directly(admin_client, trainer_user):
    """TRN-1: an admin bypasses the gate and may delete published structure."""
    from apps.training.models import CourseLesson

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    resp = admin_client.delete(f"/api/training/lessons/{lesson.id}/")
    assert resp.status_code in (200, 204)
    assert not CourseLesson.objects.filter(id=lesson.id).exists()


# ---------------------------------------------------------------------------
# Live Session Request (Report 3 §7.5/OS.4)
# ---------------------------------------------------------------------------


def test_student_can_request_live_session(student_client, individual_user, trainer_user):
    """Report 3 §7.5: candidate requests the trainer schedule a live session."""
    from apps.training.models import LiveSessionRequest

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    resp = student_client.post(
        "/api/training/live-session-requests/",
        {"course": course.id, "note": "Prefer mornings", "preferred_times": ["2026-08-10T09:00"]},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    lsr = LiveSessionRequest.objects.get(course=course, student=individual_user)
    assert lsr.status == "pending"


def test_trainer_sees_own_course_live_session_requests(
    trainer_client, trainer_user, individual_user
):
    from apps.training.models import LiveSessionRequest

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    LiveSessionRequest.objects.create(course=course, student=individual_user, note="hi")
    resp = trainer_client.get("/api/training/live-session-requests/")
    assert resp.status_code == 200
    data = resp.data["data"]
    results = data.get("results", data) if isinstance(data, dict) else data
    assert len(results) == 1


# ---------------------------------------------------------------------------
# Completion Parameters (Report 3 §6)
# ---------------------------------------------------------------------------


def test_trainer_can_set_completion_parameters(trainer_client, trainer_user):
    """Report 3 §6.1: trainer sets which contents are mandatory for completion."""
    from apps.training.models import (
        CourseCompletionParameter,
        CourseLesson,
        LessonTopic,
        SessionContent,
        TopicSession,
    )

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    lesson = CourseLesson.objects.create(course=course, title="L", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T", order=1)
    session = TopicSession.objects.create(topic=topic, title="S", order=1)
    sc = SessionContent.objects.create(session=session, title="Content 1", order=1)

    resp = trainer_client.post(
        f"/api/training/courses/{course.id}/completion-parameters/",
        {
            "parameters": [
                {"content_type": "session_content", "content_id": sc.id, "is_mandatory": True},
            ]
        },
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert CourseCompletionParameter.objects.filter(course=course, is_mandatory=True).count() == 1


def test_progress_summary_uses_mandatory_params(admin_client, trainer_user, individual_user):
    """Report 3 §6: completion % is computed against mandatory parameters
    when set, not all progress records."""
    from apps.training.models import (
        CourseCompletionParameter,
        CourseLesson,
        CourseProgress,
        CourseRegistration,
        LessonTopic,
        SessionContent,
        TopicSession,
    )

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T", order=1)
    session = TopicSession.objects.create(topic=topic, title="S", order=1)
    sc1 = SessionContent.objects.create(session=session, title="C1", order=1)
    sc2 = SessionContent.objects.create(session=session, title="C2", order=2)
    # Only sc1 is mandatory
    CourseCompletionParameter.objects.create(
        course=course, content_type="session_content", content_id=sc1.id, is_mandatory=True
    )
    reg = CourseRegistration.objects.create(
        course=course, student=individual_user, payment_status="paid"
    )
    # Student completed sc2 (non-mandatory) but NOT sc1 (mandatory)
    CourseProgress.objects.create(
        registration=reg,
        content_type="session_content",
        content_id=sc2.id,
        is_completed=True,
    )
    resp = admin_client.get(f"/api/training/registrations/{reg.id}/progress_summary/")
    assert resp.status_code == 200
    data = resp.data["data"]
    # Mandatory completion = 0/1 = 0% (sc1 not done) -> overrides completion_pct
    assert data["mandatory_total_count"] == 1
    assert data["mandatory_completed_count"] == 0
    assert data["completion_percentage"] == 0.0


# ---------------------------------------------------------------------------
# Live Session reschedule (Report 3 §7.4/OL.2)
# ---------------------------------------------------------------------------


def test_trainer_can_reschedule_live_session(trainer_client, trainer_user, individual_user):
    """Report 3 §7.4: trainer reschedules a session; the old time + reason are recorded."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.training.models import CourseRegistration, LiveSession

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    original = timezone.now() + timedelta(days=2)
    ls = LiveSession.objects.create(
        course=course, title="Q&A", scheduled_at=original, duration_minutes=60
    )
    CourseRegistration.objects.create(course=course, student=individual_user, payment_status="paid")
    new_time = (timezone.now() + timedelta(days=5)).isoformat()
    resp = trainer_client.post(
        f"/api/training/live-sessions/{ls.id}/reschedule/",
        {"scheduled_at": new_time, "reason": "Trainer unavailable"},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    ls.refresh_from_db()
    assert ls.rescheduled_from is not None
    assert ls.reschedule_reason == "Trainer unavailable"


def test_reschedule_requires_reason(trainer_client, trainer_user):
    from django.utils import timezone

    from apps.training.models import LiveSession

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    ls = LiveSession.objects.create(
        course=course, title="Q&A", scheduled_at=timezone.now(), duration_minutes=60
    )
    resp = trainer_client.post(
        f"/api/training/live-sessions/{ls.id}/reschedule/",
        {"scheduled_at": "2026-12-01T10:00:00"},
        format="json",
    )
    assert resp.status_code == 400


def test_non_trainer_cannot_reschedule(student_client, trainer_user):
    from django.utils import timezone

    from apps.training.models import LiveSession

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    ls = LiveSession.objects.create(
        course=course, title="Q&A", scheduled_at=timezone.now(), duration_minutes=60
    )
    resp = student_client.post(
        f"/api/training/live-sessions/{ls.id}/reschedule/",
        {"scheduled_at": "2026-12-01T10:00:00", "reason": "x"},
        format="json",
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Trainer edit gating (Doc 7 §5) — reuses CourseModificationRequest
# ---------------------------------------------------------------------------


def _approve_update_request(admin_client, course, trainer_client, reason="Fix content"):
    """Helper: trainer requests an update, admin approves it. Returns the
    approved CourseModificationRequest."""
    from apps.training.models import CourseModificationRequest

    trainer_client.post(
        f"/api/training/courses/{course.id}/request-update/",
        {"request_type": "update", "reason": reason},
        format="json",
    )
    cur = CourseModificationRequest.objects.get(course=course, status="pending")
    resp = admin_client.post(
        f"/api/training/course-update-requests/{cur.id}/approve/", format="json"
    )
    assert resp.status_code == 200, resp.data
    cur.refresh_from_db()
    return cur


def test_trainer_cannot_edit_published_course_directly(trainer_client, trainer_user):
    """Doc 7 §5: a trainer must go through request_update to edit a
    published course — direct PATCH is blocked."""
    course = TrainingCourse.objects.create(
        title="Original", created_by=trainer_user, status="published"
    )
    resp = trainer_client.patch(
        f"/api/training/courses/{course.id}/", {"title": "Hacked"}, format="json"
    )
    assert resp.status_code == 403
    course.refresh_from_db()
    assert course.title == "Original"


def test_trainer_can_edit_after_admin_approval_then_approval_is_consumed(
    admin_client, trainer_client, trainer_user
):
    """Once approved, the trainer's next edit succeeds; a further edit
    without a fresh approval is blocked again."""
    course = TrainingCourse.objects.create(
        title="Original", created_by=trainer_user, status="published"
    )
    _approve_update_request(admin_client, course, trainer_client)

    resp = trainer_client.patch(
        f"/api/training/courses/{course.id}/", {"title": "Updated"}, format="json"
    )
    assert resp.status_code == 200, resp.data
    course.refresh_from_db()
    assert course.title == "Updated"

    # The approval is consumed — a second edit needs a new request.
    resp2 = trainer_client.patch(
        f"/api/training/courses/{course.id}/", {"title": "Updated Again"}, format="json"
    )
    assert resp2.status_code == 403
    course.refresh_from_db()
    assert course.title == "Updated"


def test_cj_admin_edits_published_course_directly(admin_client, trainer_user):
    """cj_admin bypasses the request/approve flow entirely."""
    course = TrainingCourse.objects.create(
        title="Original", created_by=trainer_user, status="published"
    )
    resp = admin_client.patch(
        f"/api/training/courses/{course.id}/", {"title": "Admin Edit"}, format="json"
    )
    assert resp.status_code == 200
    course.refresh_from_db()
    assert course.title == "Admin Edit"


def test_trainer_can_build_structure_while_draft(trainer_client, trainer_user):
    """First-time structure creation on a draft course is never gated."""
    from apps.training.models import CourseLesson

    course = TrainingCourse.objects.create(
        title="Draft Course", created_by=trainer_user, status="draft"
    )
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    resp = trainer_client.post(
        f"/api/training/lessons/{lesson.id}/topics/",
        {"title": "Intro", "description": ""},
        format="json",
    )
    assert resp.status_code == 201, resp.data


def test_trainer_cannot_add_topic_to_published_course_directly(trainer_client, trainer_user):
    """Doc 7 §5: adding structure to an already-published course is gated
    the same way as editing it."""
    from apps.training.models import CourseLesson, LessonTopic

    course = TrainingCourse.objects.create(
        title="Published Course", created_by=trainer_user, status="published"
    )
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    resp = trainer_client.post(
        f"/api/training/lessons/{lesson.id}/topics/",
        {"title": "New Topic", "description": ""},
        format="json",
    )
    assert resp.status_code == 403
    assert not LessonTopic.objects.filter(lesson=lesson).exists()


def test_trainer_can_add_topic_after_admin_approval(admin_client, trainer_client, trainer_user):
    from apps.training.models import CourseLesson, LessonTopic

    course = TrainingCourse.objects.create(
        title="Published Course", created_by=trainer_user, status="published"
    )
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    _approve_update_request(admin_client, course, trainer_client)

    resp = trainer_client.post(
        f"/api/training/lessons/{lesson.id}/topics/",
        {"title": "New Topic", "description": ""},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert LessonTopic.objects.filter(lesson=lesson, title="New Topic").exists()


def test_cj_admin_can_add_topic_to_published_course_directly(admin_client, trainer_user):
    from apps.training.models import CourseLesson

    course = TrainingCourse.objects.create(
        title="Published Course", created_by=trainer_user, status="published"
    )
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    resp = admin_client.post(
        f"/api/training/lessons/{lesson.id}/topics/",
        {"title": "Admin Topic", "description": ""},
        format="json",
    )
    assert resp.status_code == 201, resp.data


def _course_with_assignment(trainer_user, deadline=None):
    from apps.training.models import Assignment, CourseLesson, LessonTopic, TopicSession

    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T1", order=1)
    session = TopicSession.objects.create(topic=topic, title="S1", order=1)
    assignment = Assignment.objects.create(
        session=session, title="A1", report_submission_enabled=True,
        submission_deadline=deadline,
    )
    return course, assignment


def test_past_deadline_blocks_submission(student_client, individual_user, trainer_user):
    """E-X7 baseline: a past global deadline blocks submission."""
    from django.utils import timezone
    from datetime import timedelta

    course, assignment = _course_with_assignment(
        trainer_user, deadline=timezone.now() - timedelta(days=1)
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/assignment_reports/",
        {"assignment": assignment.id, "report_text": "late"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "deadline_passed"


def test_deadline_override_allows_late_submission(
    student_client, individual_user, trainer_user
):
    """E-X7: a per-student override deadline in the future re-opens submission."""
    from django.utils import timezone
    from datetime import timedelta
    from apps.training.models import AssignmentDeadlineOverride

    course, assignment = _course_with_assignment(
        trainer_user, deadline=timezone.now() - timedelta(days=1)
    )
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    AssignmentDeadlineOverride.objects.create(
        assignment=assignment, student=individual_user,
        new_deadline=timezone.now() + timedelta(days=3),
    )
    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/assignment_reports/",
        {"assignment": assignment.id, "report_text": "on time now"},
        format="json",
    )
    assert resp.status_code == 201, resp.data


def test_trainer_sets_deadline_override(trainer_client, individual_user, trainer_user):
    """E-X7: trainer sets an override via the endpoint."""
    from django.utils import timezone
    from datetime import timedelta
    from apps.training.models import AssignmentDeadlineOverride

    course, assignment = _course_with_assignment(trainer_user)
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    new_deadline = (timezone.now() + timedelta(days=5)).isoformat()
    resp = trainer_client.post(
        f"/api/training/registrations/{reg.id}/set-deadline-override/",
        {"assignment_id": assignment.id, "new_deadline": new_deadline, "reason": "extra time"},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert AssignmentDeadlineOverride.objects.filter(
        assignment=assignment, student=individual_user
    ).exists()


def test_multiple_report_files_attached(student_client, individual_user, trainer_user):
    """E-X7: multiple files attach to a report submission."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    course, assignment = _course_with_assignment(trainer_user)
    reg = CourseRegistration.objects.create(course=course, student=individual_user)
    f1 = SimpleUploadedFile("a.pdf", b"pdf-bytes", content_type="application/pdf")
    f2 = SimpleUploadedFile("b.docx", b"doc-bytes")
    resp = student_client.post(
        f"/api/training/registrations/{reg.id}/assignment_reports/",
        {"assignment": assignment.id, "report_text": "multi", "report_files": [f1, f2]},
        format="multipart",
    )
    assert resp.status_code == 201, resp.data
    assert len(resp.data["data"]["files"]) == 2
