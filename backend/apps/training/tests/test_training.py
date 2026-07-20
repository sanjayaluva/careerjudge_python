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
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="published")
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


def test_add_lesson_to_course(trainer_client, trainer_user):
    course = TrainingCourse.objects.create(title="C", created_by=trainer_user, status="draft")
    resp = trainer_client.post(
        f"/api/training/courses/{course.id}/lessons/",
        {"title": "Lesson 1", "week_number": 1, "order": 1},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["title"] == "Lesson 1"


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
