"""Tests for Live Session consent + Interactive Questions (SRS §5 + §2.3.1).

Covers:
  - Live session consent: student consents/declines, trainer views list
  - Notify students: trainer triggers manual notification
  - Signal: creating a live session notifies registered students
  - Interactive questions: create + list via session content endpoint
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification
from apps.training.models import (
    CourseLesson,
    CourseRegistration,
    InteractiveQuestion,
    LessonTopic,
    LiveSession,
    LiveSessionConsent,
    SessionContent,
    TopicSession,
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
def trainer_user(db, roles):
    role = roles["trainer"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="training", action=action)
    return UserFactory(role=role, email="trainer@test.com")


@pytest.fixture
def student_user(db, roles):
    role = roles["individual"]
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(role=role, module="training", action=action)
    return UserFactory(role=role, email="student@test.com")


@pytest.fixture
def trainer_client(db, trainer_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(trainer_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def student_client(db, student_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(student_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


def _make_course_with_session_and_content(trainer_user):
    """Helper: create a course with a lesson > topic > session > content."""
    course = TrainingCourse.objects.create(
        title="C", created_by=trainer_user, status="published", course_type="online_standard"
    )
    lesson = CourseLesson.objects.create(course=course, title="L1", order=1)
    topic = LessonTopic.objects.create(lesson=lesson, title="T1", order=1)
    session = TopicSession.objects.create(topic=topic, title="S1", order=1)
    content = SessionContent.objects.create(
        session=session, title="Video 1", content_format="video", order=1, duration_seconds=300
    )
    return course, session, content


# ---------------------------------------------------------------------------
# Live Session Consent tests (SRS §5)
# ---------------------------------------------------------------------------


def test_student_consents_to_live_session(student_client, student_user, trainer_user):
    """SRS §5: student clicks 'Consent' button."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    live = LiveSession.objects.create(
        course=course, title="Zoom Q&A", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    resp = student_client.post(
        f"/api/training/live-sessions/{live.id}/consent/",
        {"status": "consented"},
        format="json",
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    consent = LiveSessionConsent.objects.get(live_session=live, student=student_user)
    assert consent.status == "consented"


def test_student_declines_live_session(student_client, student_user, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    live = LiveSession.objects.create(
        course=course, title="Zoom Q&A", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    resp = student_client.post(
        f"/api/training/live-sessions/{live.id}/consent/",
        {"status": "declined"},
        format="json",
    )
    assert resp.status_code == 200
    consent = LiveSessionConsent.objects.get(live_session=live, student=student_user)
    assert consent.status == "declined"


def test_consent_is_idempotent(student_client, student_user, trainer_user):
    """Consenting twice updates the existing record (no duplicates)."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    live = LiveSession.objects.create(
        course=course, title="Q&A", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    student_client.post(f"/api/training/live-sessions/{live.id}/consent/", {"status": "consented"})
    student_client.post(f"/api/training/live-sessions/{live.id}/consent/", {"status": "declined"})
    assert LiveSessionConsent.objects.filter(live_session=live, student=student_user).count() == 1
    consent = LiveSessionConsent.objects.get(live_session=live, student=student_user)
    assert consent.status == "declined"  # updated to latest


def test_trainer_views_consent_list(trainer_client, trainer_user, student_user):
    """SRS §5: trainer sees who consented."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    live = LiveSession.objects.create(
        course=course, title="Q&A", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    LiveSessionConsent.objects.create(live_session=live, student=student_user, status="consented")

    resp = trainer_client.get(f"/api/training/live-sessions/{live.id}/consents/")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1
    assert resp.data["data"][0]["student_email"] == "student@test.com"
    assert resp.data["data"][0]["status"] == "consented"


def test_student_cannot_view_consent_list(student_client, trainer_user, student_user):
    """Only the trainer or admin can view the consent list."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    live = LiveSession.objects.create(
        course=course, title="Q&A", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    resp = student_client.get(f"/api/training/live-sessions/{live.id}/consents/")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Notify Students tests (SRS §5)
# ---------------------------------------------------------------------------


def test_notify_students_sends_notifications(trainer_client, trainer_user, student_user):
    """SRS §5: trainer clicks 'Notify' button, students get notifications."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    CourseRegistration.objects.create(course=course, student=student_user, payment_status="paid")
    live = LiveSession.objects.create(
        course=course, title="Q&A", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    resp = trainer_client.post(f"/api/training/live-sessions/{live.id}/notify_students/")
    assert resp.status_code == 200
    assert resp.data["data"]["notified_count"] == 1
    # Check the notification was created
    notif = Notification.objects.filter(recipient=student_user, title__icontains="Q&A")
    assert notif.exists()


def test_student_cannot_notify_students(student_client, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    live = LiveSession.objects.create(
        course=course, title="Q&A", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    resp = student_client.post(f"/api/training/live-sessions/{live.id}/notify_students/")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Signal tests (SRS §5)
# ---------------------------------------------------------------------------


def test_creating_live_session_notifies_registered_students(trainer_user, student_user):
    """SRS §5: when a live session is created, registered students are notified
    automatically via the post_save signal.
    """
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    CourseRegistration.objects.create(course=course, student=student_user, payment_status="paid")
    # Creating a live session should fire the signal
    LiveSession.objects.create(
        course=course, title="Welcome Session", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    notif = Notification.objects.filter(recipient=student_user, title__icontains="Welcome Session")
    assert notif.exists()
    assert "live_session" in notif.first().link


def test_consenting_notifies_trainer(trainer_user, student_user, student_client):
    """SRS §5: 'notification goes back to trainer about student participation.'"""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    live = LiveSession.objects.create(
        course=course, title="Q&A", mode="online", scheduled_at="2026-08-01T10:00:00Z"
    )
    student_client.post(f"/api/training/live-sessions/{live.id}/consent/", {"status": "consented"})

    notif = Notification.objects.filter(recipient=trainer_user, title__icontains="consented")
    assert notif.exists()


# ---------------------------------------------------------------------------
# Interactive Questions tests (SRS §2.3.1 Timeliner)
# ---------------------------------------------------------------------------


def test_create_interactive_question(trainer_client, trainer_user):
    """SRS §2.3.1: trainer adds an interactive question at a specific timestamp."""
    course, session, content = _make_course_with_session_and_content(trainer_user)
    resp = trainer_client.post(
        f"/api/training/contents/{content.id}/interactive_questions/",
        {
            "question_text": "What is 2+2?",
            "trigger_timestamp": 30.0,
            "options": [
                {"id": 1, "text": "3", "is_correct": False},
                {"id": 2, "text": "4", "is_correct": True},
                {"id": 3, "text": "5", "is_correct": False},
            ],
            "correct_jump_to": 60.0,
            "incorrect_jump_to": 15.0,
        },
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    q = InteractiveQuestion.objects.get(id=resp.data["data"]["id"])
    assert q.question_text == "What is 2+2?"
    assert q.trigger_timestamp == 30.0
    assert q.correct_jump_to == 60.0
    assert q.incorrect_jump_to == 15.0
    assert len(q.options) == 3
    assert q.correct_option_id == 2


def test_list_interactive_questions(trainer_client, trainer_user):
    """SRS §2.3.1: list questions ordered by trigger_timestamp."""
    course, session, content = _make_course_with_session_and_content(trainer_user)
    InteractiveQuestion.objects.create(
        session_content=content,
        question_text="Q2",
        trigger_timestamp=60.0,
        options=[{"id": 1, "text": "A", "is_correct": True}],
        correct_jump_to=90.0,
        incorrect_jump_to=30.0,
    )
    InteractiveQuestion.objects.create(
        session_content=content,
        question_text="Q1",
        trigger_timestamp=30.0,
        options=[{"id": 1, "text": "A", "is_correct": True}],
        correct_jump_to=60.0,
        incorrect_jump_to=15.0,
    )
    resp = trainer_client.get(f"/api/training/contents/{content.id}/interactive_questions/")
    assert resp.status_code == 200
    questions = resp.data["data"]
    assert len(questions) == 2
    # Ordered by trigger_timestamp
    assert questions[0]["trigger_timestamp"] == 30.0
    assert questions[1]["trigger_timestamp"] == 60.0


def test_interactive_questions_nested_in_content(trainer_client, trainer_user):
    """The SessionContentSerializer includes interactive_questions as a nested field."""
    course, session, content = _make_course_with_session_and_content(trainer_user)
    InteractiveQuestion.objects.create(
        session_content=content,
        question_text="Q1",
        trigger_timestamp=30.0,
        options=[{"id": 1, "text": "A", "is_correct": True}],
        correct_jump_to=60.0,
        incorrect_jump_to=15.0,
    )
    # The course detail endpoint includes nested contents -> interactive_questions
    resp = trainer_client.get(f"/api/training/courses/{course.id}/")
    assert resp.status_code == 200
    lessons = resp.data["data"]["lessons"]
    contents = lessons[0]["topics"][0]["sessions"][0]["contents"]
    assert len(contents[0]["interactive_questions"]) == 1
    assert contents[0]["interactive_questions"][0]["question_text"] == "Q1"
