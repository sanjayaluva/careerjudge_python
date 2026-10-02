"""Report 9 #17: an organization manager views the course progress of his
members (his group's for a Group Admin) in a licensed course — one list,
scoped to the members he manages."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.organizations.models import (
    Group,
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)
from apps.training.models import (
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


def _user(roles, role, email):
    return User.objects.create_user(
        email=email, password="pw", is_active=True, role=roles[role], full_name=email
    )


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def world(roles):
    org = Organization.objects.create(name="Own Corp", type="corporate")
    other = Organization.objects.create(name="Other Corp", type="corporate")
    sales = Group.objects.create(organization=org, name="Sales")
    ops = Group.objects.create(organization=org, name="Ops")
    corp_admin = _user(roles, "corp_admin", "mgr@t.com")
    OrganizationMember.objects.create(organization=org, user=corp_admin, is_admin=True)
    corp_excl = _user(roles, "corp_exclusive", "ce@t.com")
    OrganizationMember.objects.create(organization=org, user=corp_excl, is_admin=True)
    group_admin = _user(roles, "group_admin", "ga@t.com")
    OrganizationMember.objects.create(organization=org, user=group_admin, group=sales)
    emp = _user(roles, "individual", "emp@t.com")
    OrganizationMember.objects.create(organization=org, user=emp, group=sales)
    ops_emp = _user(roles, "individual", "ops@t.com")
    OrganizationMember.objects.create(organization=org, user=ops_emp, group=ops)
    outsider = _user(roles, "individual", "out@t.com")
    other_admin = _user(roles, "corp_admin", "mgr2@t.com")
    OrganizationMember.objects.create(organization=other, user=other_admin, is_admin=True)

    course = TrainingCourse.objects.create(title="Licensed", status="published")
    lesson = CourseLesson.objects.create(course=course, title="L1")
    topic = LessonTopic.objects.create(lesson=lesson, title="T1")
    session = TopicSession.objects.create(topic=topic, title="S1")
    content = SessionContent.objects.create(session=session, title="Intro", order=1)
    SessionContent.objects.create(session=session, title="More", order=2)
    OrganizationAssignment.objects.create(
        organization=org, item_type="training_course", item_id=course.id
    )
    unlicensed = TrainingCourse.objects.create(title="Unlicensed", status="published")

    for student in (emp, ops_emp, outsider):
        CourseRegistration.objects.create(course=course, student=student, payment_status="paid")
    reg = CourseRegistration.objects.get(course=course, student=emp)
    CourseProgress.objects.create(
        registration=reg,
        content_type="session_content",
        content_id=content.id,
        is_completed=True,
        last_accessed_at=timezone.now(),
    )
    return {
        "org": org,
        "corp_admin": corp_admin,
        "corp_excl": corp_excl,
        "group_admin": group_admin,
        "other_admin": other_admin,
        "emp": emp,
        "course": course,
        "unlicensed": unlicensed,
    }


def _url(world, course=None):
    course = course or world["course"]
    return f"/api/organizations/{world['org'].id}/courses/{course.id}/progress/"


def _emails(resp):
    return {r["email"] for r in resp.data["data"]["learners"]}


@pytest.mark.parametrize("who", ["corp_admin", "corp_excl"])
def test_manager_sees_his_members_progress(world, who):
    resp = _client(world[who]).get(_url(world))
    assert resp.status_code == 200, resp.data
    assert resp.data["data"]["course"]["title"] == "Licensed"
    # His members only — not a learner from outside the organization.
    assert _emails(resp) == {"emp@t.com", "ops@t.com"}
    emp = next(r for r in resp.data["data"]["learners"] if r["email"] == "emp@t.com")
    assert emp["completion_status"] == "in_progress"
    assert (emp["completed_count"], emp["total_count"], emp["completion_percentage"]) == (
        1,
        2,
        50.0,
    )
    assert emp["last_activity_at"] is not None


def test_group_admin_sees_only_his_group(world):
    resp = _client(world["group_admin"]).get(_url(world))
    assert resp.status_code == 200, resp.data
    assert _emails(resp) == {"emp@t.com"}


def test_progress_needs_a_licensed_course_and_own_organization(world):
    mgr = _client(world["corp_admin"])
    assert mgr.get(_url(world, world["unlicensed"])).status_code == 404
    assert _client(world["other_admin"]).get(_url(world)).status_code == 404
    # A member (learner) cannot see his colleagues' progress.
    assert _client(world["emp"]).get(_url(world)).status_code in (403, 404)
