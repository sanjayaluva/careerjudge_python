"""Report 9 (1 Oct 2026): content licensed to organizations, and managers
acting on behalf of their members.

#98/#100-#103 licensing (courses, counselling, CP assessments), #14/#52 course
visibility, #15/#28/#59 assign/unassign courses, #16/#29/#60 course schedules,
#18/#19/#30/#31/#61 counselling booked for members.

Rights come from the real role table so the managers hold exactly the rights
they hold in production.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment
from apps.counseling.models import CounselingSession, CounsellorProfile, TimeSlot
from apps.notifications.models import Notification
from apps.organizations.models import (
    CourseSchedule,
    Group,
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)
from apps.training.models import CourseProgress, CourseRegistration, TrainingCourse

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _auth(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


def _user(roles, role, email):
    return User.objects.create_user(
        email=email, password="pw", is_active=True, role=roles[role], full_name=email
    )


def _data(resp):
    body = resp.data.get("data", resp.data)
    return body["results"] if isinstance(body, dict) and "results" in body else body


def _license(org, item_type, item_id=0):
    return OrganizationAssignment.objects.create(
        organization=org, item_type=item_type, item_id=item_id
    )


@pytest.fixture
def world(roles):
    org = Organization.objects.create(name="Own Corp", type="corporate")
    other = Organization.objects.create(name="Other Corp", type="corporate")
    cp_org = Organization.objects.create(name="Partner Org", type="channel_partner")
    sales = Group.objects.create(organization=org, name="Sales")
    ops = Group.objects.create(organization=org, name="Ops")

    corp_admin = _user(roles, "corp_admin", "mgr@t.com")
    OrganizationMember.objects.create(organization=org, user=corp_admin, is_admin=True)
    group_admin = _user(roles, "group_admin", "ga@t.com")
    OrganizationMember.objects.create(organization=org, user=group_admin, group=sales)
    emp = _user(roles, "individual", "emp@t.com")
    OrganizationMember.objects.create(organization=org, user=emp, group=sales)
    ops_emp = _user(roles, "individual", "ops@t.com")
    OrganizationMember.objects.create(organization=org, user=ops_emp, group=ops)
    stranger = _user(roles, "individual", "stranger@t.com")
    OrganizationMember.objects.create(organization=other, user=stranger)
    partner = _user(roles, "channel_partner", "cp@t.com")
    OrganizationMember.objects.create(organization=cp_org, user=partner, is_admin=True)
    cp_user = _user(roles, "individual", "cpuser@t.com")
    OrganizationMember.objects.create(organization=cp_org, user=cp_user)
    loner = _user(roles, "individual", "loner@t.com")

    cj = _user(roles, "cj_admin", "cj@t.com")
    licensed = TrainingCourse.objects.create(title="Licensed", status="published", price=100)
    unlicensed = TrainingCourse.objects.create(title="Unlicensed", status="published")
    draft = TrainingCourse.objects.create(title="Draft", status="draft")
    return {
        "org": org,
        "other": other,
        "cp_org": cp_org,
        "sales": sales,
        "ops": ops,
        "corp_admin": corp_admin,
        "group_admin": group_admin,
        "emp": emp,
        "ops_emp": ops_emp,
        "stranger": stranger,
        "partner": partner,
        "cp_user": cp_user,
        "loner": loner,
        "cj": cj,
        "licensed": licensed,
        "unlicensed": unlicensed,
        "draft": draft,
    }


# --- licensing (#98/#100-#103) ----------------------------------------------


def test_cj_admin_licenses_published_courses_and_counselling(world):
    url = f"/api/organizations/{world['org'].id}/assignments/"
    cj = _auth(world["cj"])
    ok = cj.post(url, {"item_type": "training_course", "item_id": world["licensed"].id})
    assert ok.status_code == 201, ok.data
    assert ok.data["data"]["item_title"] == "Licensed"
    draft = cj.post(url, {"item_type": "training_course", "item_id": world["draft"].id})
    assert draft.status_code == 400
    counsel = cj.post(url, {"item_type": "counseling"}, format="json")
    assert counsel.status_code == 201, counsel.data
    assert counsel.data["data"]["item_id"] == 0
    assert cj.post(url, {"item_type": "counseling"}, format="json").status_code == 400
    # Managers read the licensed list (with titles) but cannot change it.
    mgr = _auth(world["corp_admin"])
    titles = {a["item_title"] for a in _data(mgr.get(url))}
    assert titles == {"Licensed", "Counselling services"}
    body = {"item_type": "training_course", "item_id": world["unlicensed"].id}
    assert mgr.post(url, body).status_code == 403


def test_channel_partner_users_see_only_licensed_assessments(world):
    """#57/#102: the users a channel partner adds are scoped like corporate
    employees."""
    licensed = Assessment.objects.create(title="Licensed A", status="published")
    Assessment.objects.create(title="Other A", status="published")
    _license(world["cp_org"], "assessment", licensed.id)
    for who in ("cp_user", "partner"):
        ids = {a["id"] for a in _data(_auth(world[who]).get("/api/assessments/"))}
        assert ids == {licensed.id}, who
    loner_ids = {a["id"] for a in _data(_auth(world["loner"]).get("/api/assessments/"))}
    assert licensed.id in loner_ids and len(loner_ids) == 2


# --- course visibility (#14/#52) --------------------------------------------


def test_members_and_managers_see_only_licensed_courses(world):
    _license(world["org"], "training_course", world["licensed"].id)
    _license(world["cp_org"], "training_course", world["licensed"].id)
    for who in ("emp", "corp_admin", "cp_user"):
        ids = {c["id"] for c in _data(_auth(world[who]).get("/api/training/courses/"))}
        assert ids == {world["licensed"].id}, who
    # A member of an organization with no licensed courses sees none.
    assert _data(_auth(world["stranger"]).get("/api/training/courses/")) == []
    # A plain individual still sees every published course.
    ids = {c["id"] for c in _data(_auth(world["loner"]).get("/api/training/courses/"))}
    assert ids == {world["licensed"].id, world["unlicensed"].id}
    # The unlicensed course cannot be opened by id either.
    resp = _auth(world["emp"]).get(f"/api/training/courses/{world['unlicensed'].id}/")
    assert resp.status_code == 404


def test_member_self_registration_for_licensed_course_is_free(world):
    _license(world["org"], "training_course", world["licensed"].id)
    form = {
        "first_name": "E",
        "last_name": "M",
        "gender": "female",
        "mobile": "9999999999",
        "state_province": "KA",
        "city": "Bengaluru",
        "occupation": "Engineer",
        "highest_education": "BE",
        "work_experience": "2",
        "institution_name": "X",
        "place_of_institution": "Y",
    }
    resp = _auth(world["emp"]).post(
        f"/api/training/courses/{world['licensed'].id}/register/", {"form": form}, format="json"
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["payment_status"] == "paid"


# --- assign / unassign on behalf (#15/#28/#59) ------------------------------


def test_manager_assigns_and_unassigns_licensed_course(world):
    _license(world["org"], "training_course", world["licensed"].id)
    c = _auth(world["corp_admin"])
    base = f"/api/organizations/{world['org'].id}/courses/"
    resp = c.post(
        f"{base}{world['licensed'].id}/assign/", {"user_ids": [world["emp"].id]}, format="json"
    )
    assert resp.status_code == 200, resp.data
    reg = CourseRegistration.objects.get(course=world["licensed"], student=world["emp"])
    assert reg.payment_status == "paid"  # licensed: the member does not pay
    assert reg.organization_id == world["org"].id and reg.assigned_by_id == world["corp_admin"].id
    assert Notification.objects.filter(recipient=world["emp"], title__icontains="assigned").exists()

    listing = _data(c.get(base))
    assert [m["user_id"] for m in listing[0]["members"]] == [world["emp"].id]
    assert listing[0]["members"][0]["can_unassign"] is True

    resp = c.post(f"{base}{world['licensed'].id}/unassign/", {"user_id": world["emp"].id})
    assert resp.status_code == 200, resp.data
    assert not CourseRegistration.objects.filter(id=reg.id).exists()


def test_assign_refuses_non_members_and_unlicensed_courses(world):
    _license(world["org"], "training_course", world["licensed"].id)
    c = _auth(world["corp_admin"])
    base = f"/api/organizations/{world['org'].id}/courses/"
    refused = c.post(
        f"{base}{world['licensed'].id}/assign/", {"user_ids": [world["stranger"].id]}, format="json"
    )
    assert refused.status_code == 403
    unlicensed = c.post(
        f"{base}{world['unlicensed'].id}/assign/", {"user_ids": [world["emp"].id]}, format="json"
    )
    assert unlicensed.status_code == 404
    # Another organization's routes are out of reach.
    other = c.get(f"/api/organizations/{world['other'].id}/courses/")
    assert other.status_code == 404
    assert not CourseRegistration.objects.exists()


def test_group_admin_assigns_only_to_his_group(world):
    _license(world["org"], "training_course", world["licensed"].id)
    c = _auth(world["group_admin"])
    url = f"/api/organizations/{world['org'].id}/courses/{world['licensed'].id}/assign/"
    assert c.post(url, {"user_ids": [world["ops_emp"].id]}, format="json").status_code == 403
    assert c.post(url, {"user_ids": [world["emp"].id]}, format="json").status_code == 200


def test_channel_partner_assigns_to_his_users(world):
    _license(world["cp_org"], "training_course", world["licensed"].id)
    c = _auth(world["partner"])
    url = f"/api/organizations/{world['cp_org'].id}/courses/{world['licensed'].id}/assign/"
    assert c.post(url, {"user_ids": [world["cp_user"].id]}, format="json").status_code == 200
    assert c.post(url, {"user_ids": [world["emp"].id]}, format="json").status_code == 403


def test_started_course_cannot_be_unassigned(world):
    _license(world["org"], "training_course", world["licensed"].id)
    c = _auth(world["corp_admin"])
    base = f"/api/organizations/{world['org'].id}/courses/{world['licensed'].id}/"
    c.post(f"{base}assign/", {"user_ids": [world["emp"].id]}, format="json")
    reg = CourseRegistration.objects.get(student=world["emp"])
    CourseProgress.objects.create(registration=reg, content_type="content", content_id=1)
    resp = c.post(f"{base}unassign/", {"user_id": world["emp"].id})
    assert resp.status_code == 400
    assert CourseRegistration.objects.filter(id=reg.id).exists()


# --- course schedules (#16/#29/#60) -----------------------------------------


def test_course_schedule_create_reschedule_cancel_notify_members(world):
    _license(world["org"], "training_course", world["licensed"].id)
    c = _auth(world["corp_admin"])
    url = f"/api/organizations/{world['org'].id}/course-schedules/"
    when = (timezone.now() + timedelta(days=2)).isoformat()
    refused = c.post(url, {"course": world["unlicensed"].id, "scheduled_at": when})
    assert refused.status_code == 403
    created = c.post(url, {"course": world["licensed"].id, "scheduled_at": when})
    assert created.status_code == 201, created.data
    sid = created.data["data"]["id"]
    titles = lambda u: set(  # noqa: E731
        Notification.objects.filter(recipient=u).values_list("title", flat=True)
    )
    assert "Course scheduled" in titles(world["emp"]) and "Course scheduled" in titles(
        world["ops_emp"]
    )
    later = (timezone.now() + timedelta(days=5)).replace(microsecond=0)
    moved = c.patch(f"{url}{sid}/", {"scheduled_at": later.isoformat()}, format="json")
    assert moved.status_code == 200, moved.data
    assert CourseSchedule.objects.get(id=sid).scheduled_at == later
    assert "Course rescheduled" in titles(world["emp"])
    assert c.delete(f"{url}{sid}/").status_code == 200
    assert not CourseSchedule.objects.filter(id=sid).exists()
    assert "Course schedule cancelled" in titles(world["emp"])
    # The organization's admin is not notified as a learner.
    assert not titles(world["corp_admin"])


def test_group_admin_schedules_courses_only_for_his_group(world):
    _license(world["org"], "training_course", world["licensed"].id)
    c = _auth(world["group_admin"])
    url = f"/api/organizations/{world['org'].id}/course-schedules/"
    when = (timezone.now() + timedelta(days=2)).isoformat()
    body = {"course": world["licensed"].id, "scheduled_at": when}
    assert c.post(url, {**body, "group": world["ops"].id}).status_code == 403
    assert c.post(url, body).status_code == 403  # whole organization
    assert c.post(url, {**body, "group": world["sales"].id}).status_code == 201
    assert not Notification.objects.filter(recipient=world["ops_emp"]).exists()


# --- counselling for members (#18/#19/#30/#31/#61) --------------------------


@pytest.fixture
def counsellor(roles):
    user = _user(roles, "counsellor", "coun@t.com")
    profile = CounsellorProfile.objects.create(user=user)
    start = timezone.now() + timedelta(days=3)
    slots = [
        TimeSlot.objects.create(
            counsellor=profile,
            start_time=start + timedelta(hours=i),
            end_time=start + timedelta(hours=i, minutes=50),
        )
        for i in range(3)
    ]
    return profile, slots


def _book(client, org, member, counsellor, slot):
    return client.post(
        f"/api/organizations/{org.id}/counseling-sessions/",
        {
            "counselee": member.id,
            "counsellor": counsellor.id,
            "timeslot": slot.id,
            "topic": "Career growth",
        },
        format="json",
    )


def test_counselling_needs_a_licence(world, counsellor):
    profile, slots = counsellor
    c = _auth(world["corp_admin"])
    assert c.get(f"/api/organizations/{world['org'].id}/counsellors/").status_code == 403
    assert _book(c, world["org"], world["emp"], profile, slots[0]).status_code == 403
    assert not CounselingSession.objects.exists()


def test_manager_books_reschedules_and_cancels_for_member(world, counsellor):
    profile, slots = counsellor
    _license(world["org"], "counseling")
    c = _auth(world["corp_admin"])
    base = f"/api/organizations/{world['org'].id}/"
    counsellors = _data(c.get(f"{base}counsellors/"))
    assert [x["id"] for x in counsellors] == [profile.id]
    open_slots = _data(c.get(f"{base}counsellors/{profile.id}/timeslots/"))
    assert len(open_slots) == 3

    resp = _book(c, world["org"], world["emp"], profile, slots[0])
    assert resp.status_code == 201, resp.data
    session = CounselingSession.objects.get()
    assert session.counselee_id == world["emp"].id
    assert float(session.fee) == 0 and session.payment_status == "paid"
    assert session.organization_id == world["org"].id
    assert Notification.objects.filter(recipient=profile.user).exists()
    assert Notification.objects.filter(recipient=world["emp"]).exists()
    # The booked slot is no longer offered.
    assert len(_data(c.get(f"{base}counsellors/{profile.id}/timeslots/"))) == 2
    # The member sees the session among his own.
    mine = _data(_auth(world["emp"]).get("/api/counseling/sessions/"))
    assert [s["id"] for s in mine] == [session.id]

    moved = c.post(
        f"{base}counseling-sessions/{session.id}/reschedule/",
        {"timeslot": slots[1].id},
        format="json",
    )
    assert moved.status_code == 200, moved.data
    session.refresh_from_db()
    slots[0].refresh_from_db()
    assert session.timeslot_id == slots[1].id and session.status == "pending"
    assert slots[0].status == "available"

    no_reason = c.post(f"{base}counseling-sessions/{session.id}/cancel/", {}, format="json")
    assert no_reason.status_code == 400
    cancelled = c.post(
        f"{base}counseling-sessions/{session.id}/cancel/", {"reason": "Clash"}, format="json"
    )
    assert cancelled.status_code == 200, cancelled.data
    session.refresh_from_db()
    assert session.status == "cancelled"
    assert session.cancellation.cancelled_by == "organization"
    assert _data(c.get(f"{base}counseling-sessions/"))[0]["status"] == "cancelled"


def test_counselling_cannot_be_booked_for_non_members(world, counsellor):
    profile, slots = counsellor
    _license(world["org"], "counseling")
    _license(world["other"], "counseling")
    c = _auth(world["corp_admin"])
    assert _book(c, world["org"], world["stranger"], profile, slots[0]).status_code == 403
    # Not via the other organization's route either.
    assert _book(c, world["other"], world["stranger"], profile, slots[0]).status_code == 404
    # A Group Admin books only for his group.
    ga = _auth(world["group_admin"])
    assert _book(ga, world["org"], world["ops_emp"], profile, slots[0]).status_code == 403
    assert _book(ga, world["org"], world["emp"], profile, slots[0]).status_code == 201
    assert not CounselingSession.objects.filter(counselee=world["ops_emp"]).exists()


def test_channel_partner_books_counselling_for_his_user(world, counsellor):
    profile, slots = counsellor
    _license(world["cp_org"], "counseling")
    c = _auth(world["partner"])
    assert _book(c, world["cp_org"], world["cp_user"], profile, slots[0]).status_code == 201
    assert _book(c, world["cp_org"], world["emp"], profile, slots[1]).status_code == 403
    # The same slot cannot be booked twice.
    assert _book(c, world["cp_org"], world["cp_user"], profile, slots[0]).status_code == 400
