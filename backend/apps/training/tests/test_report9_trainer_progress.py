"""Report 8.1 #62: the trainer sees each registered learner's course progress
in one list. Report 9 #83: learners see "Name of Trainer" (an optional
trainer CJ Admin sets on the course, else the creator) and not who else
registered."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment, AssessmentSession
from apps.training.models import (
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
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _user(roles, role, email, name=""):
    return User.objects.create_user(
        email=email, password="pw", is_active=True, role=roles[role], full_name=name
    )


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def world(roles):
    trainer = _user(roles, "trainer", "tr@t.com", "Tara Trainer")
    other_trainer = _user(roles, "trainer", "tr2@t.com", "Otto Trainer")
    cj = _user(roles, "cj_admin", "cj@t.com", "CJ Admin")
    asha = _user(roles, "individual", "asha@t.com", "Asha")
    ben = _user(roles, "individual", "ben@t.com", "Ben")
    course = TrainingCourse.objects.create(title="Python", status="published", created_by=trainer)
    lesson = CourseLesson.objects.create(course=course, title="L1")
    topic = LessonTopic.objects.create(lesson=lesson, title="T1")
    session = TopicSession.objects.create(topic=topic, title="S1")
    c1 = SessionContent.objects.create(
        session=session, title="Intro", content_format="text", order=1
    )
    SessionContent.objects.create(session=session, title="More", content_format="text", order=2)
    return {
        "trainer": trainer,
        "other_trainer": other_trainer,
        "cj": cj,
        "asha": asha,
        "ben": ben,
        "course": course,
        "c1": c1,
    }


def _progress(client, course):
    return client.get(f"/api/training/courses/{course.id}/registrations-progress/")


def test_trainer_sees_each_learners_progress(world):
    course = world["course"]
    reg = CourseRegistration.objects.create(
        course=course, student=world["asha"], payment_status="paid"
    )
    CourseRegistration.objects.create(course=course, student=world["ben"], payment_status="paid")
    CourseProgress.objects.create(
        registration=reg,
        content_type="session_content",
        content_id=world["c1"].id,
        is_completed=True,
        last_accessed_at=timezone.now(),
    )
    exam = Assessment.objects.create(title="Quiz", status="published")
    CourseAssessment.objects.create(
        course=course, assessment=exam, level="end_of_course", title="Final quiz"
    )
    AssessmentSession.objects.create(
        assessment=exam,
        candidate=world["asha"],
        status="completed",
        percentage=80.0,
        completed_at=timezone.now(),
    )

    resp = _progress(_client(world["trainer"]), course)
    assert resp.status_code == 200, resp.data
    rows = {r["full_name"]: r for r in resp.data["data"]}
    asha, ben = rows["Asha"], rows["Ben"]
    assert asha["completion_status"] == "in_progress"
    assert (asha["completed_count"], asha["total_count"]) == (1, 2)
    assert asha["completion_percentage"] == 50.0
    assert asha["started_at"] and asha["last_activity_at"]
    assert asha["assessment_scores"] == [
        {
            "course_assessment_id": course.assessments.get().id,
            "title": "Final quiz",
            "percentage": 80.0,
            "status": "completed",
        }
    ]
    assert ben["completion_status"] == "not_started"
    assert ben["completion_percentage"] == 0.0
    assert ben["started_at"] is None and ben["last_activity_at"] is None
    # CJ Admin sees it too.
    assert _progress(_client(world["cj"]), course).status_code == 200


def test_progress_scoped_to_trainers_own_courses_and_hidden_from_learners(world):
    course = world["course"]
    CourseRegistration.objects.create(course=course, student=world["asha"], payment_status="paid")
    # Report 9 #84: another trainer's course is not his.
    assert _progress(_client(world["other_trainer"]), course).status_code == 404
    # Report 9 #83: a learner sees neither the progress list nor who registered.
    learner = _client(world["asha"])
    assert _progress(learner, course).status_code == 403
    assert learner.get(f"/api/training/courses/{course.id}/registrations/").status_code == 403
    trainer = _client(world["trainer"])
    assert trainer.get(f"/api/training/courses/{course.id}/registrations/").status_code == 200


def test_trainer_name_falls_back_to_creator(world):
    course = world["course"]
    resp = _client(world["asha"]).get(f"/api/training/courses/{course.id}/")
    assert resp.data["data"]["trainer"] is None
    assert resp.data["data"]["trainer_name"] == "Tara Trainer"


def test_cj_admin_names_the_course_trainer(world):
    course = TrainingCourse.objects.create(title="Admin course", created_by=world["cj"])
    cj = _client(world["cj"])
    resp = cj.patch(
        f"/api/training/courses/{course.id}/", {"trainer": world["other_trainer"].id}, format="json"
    )
    assert resp.status_code == 200, resp.data
    assert resp.data["data"]["trainer_name"] == "Otto Trainer"
    # Only a Trainer user can be named.
    resp = cj.patch(
        f"/api/training/courses/{course.id}/", {"trainer": world["asha"].id}, format="json"
    )
    assert resp.status_code == 400
    # Set when creating, too; shown in the list.
    resp = cj.post(
        "/api/training/courses/",
        {"title": "New", "trainer": world["trainer"].id},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["trainer_name"] == "Tara Trainer"
    course.status = "published"
    course.save(update_fields=["status"])
    rows = _client(world["asha"]).get("/api/training/courses/").data["data"]["results"]
    assert {r["title"]: r["trainer_name"] for r in rows}["Admin course"] == "Otto Trainer"


def test_trainer_cannot_set_the_trainer_field(world):
    course = TrainingCourse.objects.create(title="Own draft", created_by=world["trainer"])
    resp = _client(world["trainer"]).patch(
        f"/api/training/courses/{course.id}/", {"trainer": world["other_trainer"].id}, format="json"
    )
    assert resp.status_code == 400
    course.refresh_from_db()
    assert course.trainer_id is None
