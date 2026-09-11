"""Tests for the dossier "medium" training gaps (D7):

  - Resume-from-last: progress_summary's `last_content` resume point reflects
    the most-recently-accessed content, not just any record.
  - Score rolled into progress summary: assessment scores (CourseAssessment ->
    latest completed AssessmentSession) and assignment report scores
    (trainer_score) surface in progress_summary (SRS §6 "Score report").
  - Media upload: SessionContent accepts a real file upload (`media_file`)
    alongside the existing URL/base64 `content_url`.
"""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import Assessment, AssessmentSession
from apps.training.models import (
    Assignment,
    AssignmentReport,
    CourseAssessment,
    CourseLesson,
    CourseProgress,
    CourseRegistration,
    LessonTopic,
    SessionContent,
    TopicSession,
    TrainingCourse,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def trainer_user(db, roles):
    role = roles["trainer"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="training", action=action)
    return UserFactory(role=role, email="trainer2@test.com")


@pytest.fixture
def individual_user(db, roles):
    role = roles["individual"]
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(role=role, module="training", action=action)
    return UserFactory(role=role, email="student2@test.com")


@pytest.fixture
def student_client(db, individual_user):
    c = APIClient()
    refresh = RefreshToken.for_user(individual_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


def _make_session(topic, order=1, title="S"):
    return TopicSession.objects.create(topic=topic, title=title, order=order)


def _make_topic(course, order=1):
    lesson = CourseLesson.objects.create(course=course, title="L", order=order)
    return LessonTopic.objects.create(lesson=lesson, title="T", order=1)


# ---------------------------------------------------------------------------
# Resume-from-last (D7)
# ---------------------------------------------------------------------------


def test_resume_point_is_the_most_recently_accessed_content(
    student_client, individual_user, trainer_user
):
    """last_content in progress_summary must be the record with the latest
    last_accessed_at, not just any completed/incomplete record."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(
        course=course, student=individual_user, payment_status="paid"
    )
    now = timezone.now()
    CourseProgress.objects.create(
        registration=reg,
        content_type="session_content",
        content_id=1,
        is_completed=True,
        last_accessed_at=now - timedelta(hours=2),
    )
    CourseProgress.objects.create(
        registration=reg,
        content_type="session_content",
        content_id=2,
        is_completed=False,
        last_accessed_at=now - timedelta(minutes=5),
    )
    resp = student_client.get(f"/api/training/registrations/{reg.id}/progress_summary/")
    assert resp.status_code == 200
    assert resp.data["data"]["last_content"] == {
        "content_type": "session_content",
        "content_id": 2,
    }


# ---------------------------------------------------------------------------
# Score rolled into progress summary (D7)
# ---------------------------------------------------------------------------


def test_progress_summary_includes_assessment_scores(student_client, individual_user, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(
        course=course, student=individual_user, payment_status="paid"
    )
    assessment = Assessment.objects.create(title="Final Exam", status="published")
    ca = CourseAssessment.objects.create(
        course=course, assessment=assessment, level="end_of_course", title="Final Exam"
    )
    AssessmentSession.objects.create(
        assessment=assessment,
        candidate=individual_user,
        status="completed",
        total_score=8.0,
        max_score=10.0,
        percentage=80.0,
        completed_at=timezone.now(),
    )

    resp = student_client.get(f"/api/training/registrations/{reg.id}/progress_summary/")
    assert resp.status_code == 200
    data = resp.data["data"]
    assert len(data["assessment_scores"]) == 1
    row = data["assessment_scores"][0]
    assert row["course_assessment_id"] == ca.id
    assert row["percentage"] == 80.0
    assert row["status"] == "completed"
    assert data["average_assessment_percentage"] == 80.0


def test_progress_summary_assessment_not_attempted(student_client, individual_user, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(
        course=course, student=individual_user, payment_status="paid"
    )
    assessment = Assessment.objects.create(title="Final Exam", status="published")
    CourseAssessment.objects.create(
        course=course, assessment=assessment, level="end_of_course", title="Final Exam"
    )
    resp = student_client.get(f"/api/training/registrations/{reg.id}/progress_summary/")
    data = resp.data["data"]
    assert data["assessment_scores"][0]["status"] == "not_attempted"
    assert data["assessment_scores"][0]["percentage"] is None
    assert data["average_assessment_percentage"] is None


def test_progress_summary_includes_assignment_report_scores(
    student_client, individual_user, trainer_user
):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
    reg = CourseRegistration.objects.create(
        course=course, student=individual_user, payment_status="paid"
    )
    topic = _make_topic(course)
    session = _make_session(topic)
    assignment = Assignment.objects.create(
        session=session, title="Essay", report_submission_enabled=True
    )
    AssignmentReport.objects.create(
        assignment=assignment,
        student=individual_user,
        report_text="My essay",
        status="reviewed",
        trainer_score=7.5,
        trainer_feedback="Good work",
    )
    resp = student_client.get(f"/api/training/registrations/{reg.id}/progress_summary/")
    data = resp.data["data"]
    assert len(data["assignment_report_scores"]) == 1
    row = data["assignment_report_scores"][0]
    assert row["assignment_title"] == "Essay"
    assert row["trainer_score"] == 7.5
    assert row["status"] == "reviewed"


# ---------------------------------------------------------------------------
# Media upload + embed (D7)
# ---------------------------------------------------------------------------


def _tiny_mp4():
    return SimpleUploadedFile("clip.mp4", b"\x00\x00\x00\x18ftypmp42", content_type="video/mp4")


def test_content_accepts_media_file_upload(trainer_user):
    """A trainer uploads a real media file for session content, instead of
    only a URL/base64 string."""
    from rest_framework_simplejwt.tokens import RefreshToken

    roles = get_or_create_default_roles()
    role = roles["trainer"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="training", action=action)
    trainer = UserFactory(role=role, email="mediatrainer@test.com")
    client = APIClient()
    refresh = RefreshToken.for_user(trainer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    course = TrainingCourse.objects.create(title="C", created_by=trainer, status="draft")
    topic = _make_topic(course)
    session = _make_session(topic)

    resp = client.post(
        f"/api/training/sessions/{session.id}/contents/",
        {
            "title": "Intro video",
            "content_format": "video",
            "media_file": _tiny_mp4(),
        },
        format="multipart",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    content = SessionContent.objects.get(id=resp.data["data"]["id"])
    assert content.media_file.name
    assert resp.data["data"]["media_file"]


def test_content_media_file_embeds_alongside_text(trainer_user):
    """Text-format content can carry an uploaded media file too, so the
    player can embed it alongside the text (minimal embed support)."""
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    topic = _make_topic(course)
    session = _make_session(topic)
    content = SessionContent.objects.create(
        session=session,
        title="Notes",
        content_format="text",
        text_content="See the diagram below.",
        media_file=SimpleUploadedFile("diagram.png", b"\x89PNG", content_type="image/png"),
        order=1,
    )
    assert content.media_file.name
    assert content.text_content == "See the diagram below."
