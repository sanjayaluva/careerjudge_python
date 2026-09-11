"""Tests for the Counseling module.

Covers SRS 08_counseling_process.json:
  - Category CRUD
  - Counsellor profile CRUD
  - TimeSlot management (SRS §3.1)
  - Session booking (SRS §2.1)
  - Session confirmation (SRS §3.2)
  - Session cancellation with refund tiers (SRS §2.2)
  - Session completion (SRS §3.3)
  - Session summary (SRS §3.3)
  - Session feedback (SRS §2.3, admin-only)
  - Follow-up sessions (SRS §3.3)
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.counseling.models import (
    CounselingCategory,
    CounselingSession,
    CounsellorProfile,
    TimeSlot,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def admin_user(db, roles):
    role = roles["cj_admin"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="counseling", action=action)
    return UserFactory(role=role, email="admin@test.com")


@pytest.fixture
def counsellor_user(db, roles):
    role = roles["counsellor"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="counseling", action=action)
    return UserFactory(role=role, email="counsellor@test.com")


@pytest.fixture
def counselee_user(db, roles):
    role = roles["individual"]
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(role=role, module="counseling", action=action)
    return UserFactory(role=role, email="counselee@test.com")


@pytest.fixture
def admin_client(db, admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def counsellor_client(db, counsellor_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(counsellor_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def counselee_client(db, counselee_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(counselee_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


def _make_counsellor(user, **overrides):
    """Create a counsellor profile + return it.

    CounsellorProfile no longer stores full_name/bio/hourly_rate directly —
    those live on UserProfile. The CounsellorProfile is just a link to the
    user + categories M2M.
    """
    from apps.accounts.models import UserProfile

    # Set counsellor-specific fields on UserProfile
    up, _ = UserProfile.objects.get_or_create(user=user)
    up.bio = overrides.pop("bio", "Experienced counsellor")
    up.hourly_rate = overrides.pop("hourly_rate", 100)
    up.is_available_for_counseling = True
    up.save()

    # Set full_name on the User model
    user.full_name = overrides.pop("full_name", "Dr. Smith")
    user.save()

    return CounsellorProfile.objects.create(user=user)


def _make_timeslot(counsellor, hours_from_now=48, **overrides):
    from datetime import timedelta

    from django.utils import timezone

    start = timezone.now() + timedelta(hours=hours_from_now)
    defaults = {
        "counsellor": counsellor,
        "start_time": start,
        "end_time": start + timedelta(hours=1),
        "status": "available",
    }
    defaults.update(overrides)
    return TimeSlot.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Category tests
# ---------------------------------------------------------------------------


def test_admin_can_create_category(admin_client):
    resp = admin_client.post(
        "/api/counseling/categories/",
        {"name": "career", "description": "Career counselling"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["name"] == "career"


def test_list_categories(admin_client):
    CounselingCategory.objects.create(name="career")
    CounselingCategory.objects.create(name="emotional")
    resp = admin_client.get("/api/counseling/categories/")
    assert resp.status_code == 200
    data = resp.data["data"]
    results = data["results"] if isinstance(data, dict) and "results" in data else data
    assert len(results) == 2


# ---------------------------------------------------------------------------
# Counsellor profile tests
# ---------------------------------------------------------------------------


def test_create_counsellor_profile(counsellor_client, counsellor_user):
    resp = counsellor_client.post(
        "/api/counseling/counsellors/",
        {},
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    profile = CounsellorProfile.objects.get(id=resp.data["data"]["id"])
    assert profile.user == counsellor_user


def test_list_counsellors(counselee_client, counsellor_user):
    _make_counsellor(counsellor_user)
    resp = counselee_client.get("/api/counseling/counsellors/")
    assert resp.status_code == 200
    data = resp.data["data"]
    results = data["results"] if isinstance(data, dict) and "results" in data else data
    assert len(results) == 1


def test_counsellor_timeslots(counselee_client, counsellor_user):
    """SRS §2.1: 'System shows available timeslots of the counsellor for a week'."""
    counsellor = _make_counsellor(counsellor_user)
    _make_timeslot(counsellor, hours_from_now=24)
    _make_timeslot(counsellor, hours_from_now=48)
    resp = counselee_client.get(f"/api/counseling/counsellors/{counsellor.id}/timeslots/")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 2


# ---------------------------------------------------------------------------
# Session booking tests (SRS §2.1)
# ---------------------------------------------------------------------------


def test_counselee_books_session(counselee_client, counselee_user, counsellor_user):
    """SRS §2.1: counselee books a timeslot."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    resp = counselee_client.post(
        "/api/counseling/sessions/",
        {
            "counsellor": counsellor.id,
            "timeslot": timeslot.id,
            "topic": "Career advice",
            "description": "Need guidance on career switch",
            "terms_accepted": True,
            "mode": "online",
        },
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    session = CounselingSession.objects.get(id=resp.data["data"]["id"])
    assert session.counselee == counselee_user
    assert session.status == "pending"
    # fee is set from counsellor's hourly_rate (now on UserProfile)
    assert float(session.fee) == float(counsellor.user.profile.hourly_rate)
    timeslot.refresh_from_db()
    assert timeslot.status == "booked"


def test_cannot_book_unavailable_timeslot(counselee_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, status="booked")
    resp = counselee_client.post(
        "/api/counseling/sessions/",
        {
            "counsellor": counsellor.id,
            "timeslot": timeslot.id,
            "topic": "Test",
            "terms_accepted": True,
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "no longer available" in resp.data["error"]["message"]


def test_my_sessions(counselee_client, counselee_user, counsellor_user):
    """Counselee sees only their own sessions."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="My session",
        fee=counsellor.hourly_rate,
    )
    resp = counselee_client.get("/api/counseling/sessions/my_sessions/")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1


# ---------------------------------------------------------------------------
# Session confirmation tests (SRS §3.2)
# ---------------------------------------------------------------------------


def test_counsellor_confirms_session(counsellor_client, counselee_user, counsellor_user):
    """SRS §3.2: counsellor confirms a pending appointment."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="pending",
    )
    resp = counsellor_client.post(f"/api/counseling/sessions/{session.id}/confirm/")
    assert resp.status_code == 200
    session.refresh_from_db()
    assert session.status == "confirmed"
    assert session.confirmed_at is not None


def test_cannot_confirm_non_pending_session(counsellor_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="confirmed",
    )
    resp = counsellor_client.post(f"/api/counseling/sessions/{session.id}/confirm/")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cancellation tests (SRS §2.2)
# ---------------------------------------------------------------------------


def test_cancel_24h_before_full_refund(counselee_client, counselee_user, counsellor_user):
    """SRS §2.2: cancellation 24+ hours before → full refund."""
    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor, hours_from_now=48)  # 48h away
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee="100.00",
        status="confirmed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee", "reason": "Schedule conflict"},
        format="json",
    )
    assert resp.status_code == 200
    session.refresh_from_db()
    assert session.status == "cancelled"
    assert session.payment_status == "refunded_full"
    assert resp.data["data"]["cancellation"]["refund_tier"] == "full"
    assert resp.data["data"]["cancellation"]["refund_amount"] == "100.00"
    timeslot.refresh_from_db()
    assert timeslot.status == "available"


def test_cancel_4h_before_half_refund(counselee_client, counselee_user, counsellor_user):
    """SRS §2.2: cancellation 4+ hours before → 50% refund."""
    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor, hours_from_now=6)  # 6h away
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee="100.00",
        status="confirmed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee", "reason": "Cannot attend"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["data"]["cancellation"]["refund_tier"] == "half"
    assert resp.data["data"]["cancellation"]["refund_amount"] == "50.00"


def test_cancel_under_4h_no_refund(counselee_client, counselee_user, counsellor_user):
    """SRS §2.2: cancellation <4 hours before → no refund."""
    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor, hours_from_now=2)  # 2h away
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee="100.00",
        status="confirmed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee", "reason": "Cannot attend"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["data"]["cancellation"]["refund_tier"] == "none"
    assert resp.data["data"]["cancellation"]["refund_amount"] == "0.00"


def test_counsellor_cancellation_increments_count(
    counsellor_client, counselee_user, counsellor_user
):
    """SRS §3.2: 'System tracks cancellation frequency per counsellor.'"""
    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor, hours_from_now=48)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee="100.00",
        status="confirmed",
    )
    counsellor_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counsellor", "reason": "Emergency"},
        format="json",
    )
    # cancellation_count now lives on UserProfile
    counsellor.user.profile.refresh_from_db()
    assert counsellor.user.profile.cancellation_count == 1


# ---------------------------------------------------------------------------
# Session completion + summary (SRS §3.3)
# ---------------------------------------------------------------------------


def test_complete_session(counsellor_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="confirmed",
    )
    resp = counsellor_client.post(f"/api/counseling/sessions/{session.id}/complete/")
    assert resp.status_code == 200
    session.refresh_from_db()
    assert session.status == "completed"


def test_counsellor_saves_summary(counsellor_client, counselee_user, counsellor_user):
    """SRS §3.3: counsellor fills Session Summary Form."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    resp = counsellor_client.post(
        f"/api/counseling/sessions/{session.id}/summary/",
        {
            "summary": "Discussed career options",
            "recommendations": "Take an aptitude test",
            "followup_recommended": True,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["summary"] == "Discussed career options"
    assert resp.data["data"]["followup_recommended"] is True


def test_counselee_cannot_view_summary(
    counselee_client, counsellor_client, admin_client, counselee_user, counsellor_user
):
    """D8 §3.3: the counsellor's private summary must not leak to the counselee."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    counsellor_client.post(
        f"/api/counseling/sessions/{session.id}/summary/",
        {"summary": "Private counsellor notes"},
        format="json",
    )

    resp = counselee_client.get(f"/api/counseling/sessions/{session.id}/summary/")
    assert resp.status_code == 403

    resp = counsellor_client.get(f"/api/counseling/sessions/{session.id}/summary/")
    assert resp.status_code == 200
    assert resp.data["data"]["summary"] == "Private counsellor notes"

    resp = admin_client.get(f"/api/counseling/sessions/{session.id}/summary/")
    assert resp.status_code == 200
    assert resp.data["data"]["summary"] == "Private counsellor notes"


# ---------------------------------------------------------------------------
# Feedback tests (SRS §2.3)
# ---------------------------------------------------------------------------


def test_counselee_submits_feedback(counselee_client, counselee_user, counsellor_user):
    """SRS §2.3: counselee gives feedback after session."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/feedback/",
        {"rating": 5, "experience_text": "Very helpful session"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["rating"] == 5


def test_feedback_only_after_completion(counselee_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="confirmed",  # not completed
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/feedback/",
        {"rating": 5, "experience_text": "Good"},
        format="json",
    )
    assert resp.status_code == 403


def test_feedback_admin_only(counselee_client, counsellor_client, counselee_user, counsellor_user):
    """SRS §2.3: 'User feedbacks are available only to Admin User.'"""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    # Counselee submits feedback
    counselee_client.post(
        f"/api/counseling/sessions/{session.id}/feedback/",
        {"rating": 4, "experience_text": "Good"},
        format="json",
    )
    # Counsellor cannot view feedback (admin-only)
    resp = counsellor_client.get(f"/api/counseling/sessions/{session.id}/feedback/")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Follow-up session tests (SRS §3.3)
# ---------------------------------------------------------------------------


def test_counsellor_proposes_followup(counsellor_client, counselee_user, counsellor_user):
    """SRS §3.3: counsellor proposes a follow-up session."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    resp = counsellor_client.post(
        f"/api/counseling/sessions/{session.id}/followups/",
        {"proposed_time": "2026-08-15T10:00:00Z"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["status"] == "proposed"


def test_counselee_confirms_followup(counselee_client, counselee_user, counsellor_user):
    """SRS §3.3: counselee confirms follow-up (initiates payment)."""
    from apps.counseling.models import FollowupSession

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    followup = FollowupSession.objects.create(
        original_session=session,
        counsellor=counsellor,
        proposed_time="2026-08-15T10:00:00Z",
        status="proposed",
    )
    resp = counselee_client.post(f"/api/counseling/followups/{followup.id}/confirm/")
    assert resp.status_code == 200
    followup.refresh_from_db()
    assert followup.status == "confirmed"
    assert followup.confirmed_session is not None
    assert followup.confirmed_session.status == "confirmed"


# ---------------------------------------------------------------------------
# Report 3 Counselling — notification wiring (helpdesk + counselee + counsellor)
# ---------------------------------------------------------------------------


def test_booking_notifies_counsellor_and_helpdesk(
    counselee_client, counselee_user, counsellor_user
):
    """Report 3 §1.10: a new booking fires notifications to the counsellor + helpdesk."""
    from apps.accounts.models import Role
    from apps.notifications.models import Notification

    # Ensure the helpdesk role + a helpdesk user exist
    helpdesk_role, _ = Role.objects.get_or_create(name="helpdesk")
    helpdesk_user = UserFactory.create(role=helpdesk_role, email="helpdesk@test.com")

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    resp = counselee_client.post(
        "/api/counseling/sessions/",
        {
            "counsellor": counsellor.id,
            "timeslot": timeslot.id,
            "topic": "Career",
            "terms_accepted": True,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert Notification.objects.filter(
        recipient=counsellor_user, title__contains="New booking"
    ).exists()
    assert Notification.objects.filter(
        recipient=helpdesk_user, title__contains="counselling booking"
    ).exists()


def test_booking_requires_terms_acceptance(counselee_client, counselee_user, counsellor_user):
    """Report 3 §1.8: terms must be explicitly accepted."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    resp = counselee_client.post(
        "/api/counseling/sessions/",
        {"counsellor": counsellor.id, "timeslot": timeslot.id, "topic": "Career"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["error"]["code"] == "validation_error"
    assert "Terms" in resp.data["error"]["message"]


def test_confirm_notifies_counselee(counsellor_client, counselee_user, counsellor_user):
    """Report 3 §1.13: confirming a booking notifies the counselee."""
    from apps.notifications.models import Notification

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="x",
        fee=counsellor.hourly_rate,
    )
    resp = counsellor_client.post(f"/api/counseling/sessions/{session.id}/confirm/")
    assert resp.status_code == 200
    assert Notification.objects.filter(
        recipient=counselee_user, title__contains="confirmed"
    ).exists()


# ---------------------------------------------------------------------------
# Report 3 Counselling §2.2 — feedback form (8 fields, 1-10 scale)
# ---------------------------------------------------------------------------


def test_feedback_eight_fields_and_10_point_scale(
    counselee_client, counselee_user, counsellor_user
):
    """Report 3 §2.2: feedback accepts the 8 fields + a 1-10 rating."""
    from apps.counseling.models import SessionFeedback

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="x",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/feedback/",
        {
            "session_usefulness": "very_useful",
            "useful_reason": "Great advice",
            "counsellor_empathy": "very_much",
            "session_ended": "on_time",
            "would_rechoose": "yes",
            "rechoose_reason": "Very helpful",
            "improvement_suggestions": "More examples",
            "rating": 9,
        },
        format="json",
    )
    assert resp.status_code in (200, 201), resp.data
    fb = SessionFeedback.objects.get(session=session)
    assert fb.session_usefulness == "very_useful"
    assert fb.rating == 9


# ---------------------------------------------------------------------------
# Report 3 Counselling §2.4 — session summary (6 fields)
# ---------------------------------------------------------------------------


def test_summary_six_fields(counsellor_client, counselee_user, counsellor_user):
    """Report 3 §2.4: summary accepts the 6 mandatory/optional fields."""
    from apps.counseling.models import SessionSummary

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="x",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    resp = counsellor_client.post(
        f"/api/counseling/sessions/{session.id}/summary/",
        {
            "client_details": "Client seeking career change",
            "summary": "Discussed options",
            "provisional_diagnosis": "Career indecision",
            "case_prognosis": "Good with guidance",
            "session_smoothness": "yes",
            "smoothly_reason": "Engaged client",
            "followup_recommended": True,
        },
        format="json",
    )
    assert resp.status_code in (200, 201), resp.data
    sm = SessionSummary.objects.get(session=session)
    assert sm.client_details == "Client seeking career change"
    assert sm.session_smoothness == "yes"
    assert sm.followup_recommended is True


# ---------------------------------------------------------------------------
# Report 3 §1.1/§1.2 — timeslot edit/delete + 3-week limit
# ---------------------------------------------------------------------------


def test_counsellor_can_delete_own_available_timeslot(counsellor_client, counsellor_user):
    """Report 3 §1.1: a counsellor can delete their own (unbooked) timeslot."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, status="available")
    resp = counsellor_client.delete(f"/api/counseling/timeslots/{timeslot.id}/")
    assert resp.status_code in (200, 204), resp.data
    assert not TimeSlot.objects.filter(id=timeslot.id).exists()


def test_cannot_delete_booked_timeslot(counsellor_client, counsellor_user, counselee_user):
    """Report 3 §1.1: a booked timeslot cannot be deleted."""
    from apps.counseling.models import CounselingSession

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, status="booked")
    CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="x",
        fee=counsellor.hourly_rate,
    )
    resp = counsellor_client.delete(f"/api/counseling/timeslots/{timeslot.id}/")
    assert resp.status_code == 403
    assert "booked" in resp.data["error"]["message"]


def test_non_owner_cannot_edit_timeslot(counselee_client, counsellor_user):
    """Report 3 §1.1: only the owning counsellor (or admin) can edit a slot."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    resp = counselee_client.patch(
        f"/api/counseling/timeslots/{timeslot.id}/",
        {"status": "blocked"},
        format="json",
    )
    assert resp.status_code == 403


def test_timeslot_rejects_beyond_max_weeks(counsellor_client, counsellor_user):
    """Report 3 §1.2: cannot create a timeslot beyond the max_weeks_ahead limit."""
    from datetime import timedelta

    from django.utils import timezone

    counsellor = _make_counsellor(counsellor_user)
    too_far = (timezone.now() + timedelta(weeks=10)).isoformat()
    resp = counsellor_client.post(
        "/api/counseling/timeslots/",
        {"counsellor": counsellor.id, "start_time": too_far, "end_time": too_far},
        format="json",
    )
    assert resp.status_code == 400
    assert "weeks" in resp.data["error"]["message"]


# ---------------------------------------------------------------------------
# Report 3 §1.9/§1.11 — counseling settings (terms + refund policy)
# ---------------------------------------------------------------------------


def test_anyone_can_read_settings(counselee_client):
    """Settings (terms, refund policy) are readable by any authed user so the
    booking form can display them."""
    resp = counselee_client.get("/api/counseling/settings/")
    assert resp.status_code == 200
    assert "terms_and_conditions" in resp.data["data"]


def test_only_admin_can_update_settings(counselee_client, admin_client):
    from apps.counseling.models import CounselingSettings

    # counselee cannot patch
    resp = counselee_client.patch(
        "/api/counseling/settings/1/",
        {"terms_and_conditions": "New terms"},
        format="json",
    )
    assert resp.status_code == 403
    # admin can patch
    resp = admin_client.patch(
        "/api/counseling/settings/1/",
        {"terms_and_conditions": "New terms", "max_weeks_ahead": 5},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert CounselingSettings.get().terms_and_conditions == "New terms"
    assert CounselingSettings.get().max_weeks_ahead == 5


# ---------------------------------------------------------------------------
# Report 3 §1.17 — counsellor category tagging on add-user
# ---------------------------------------------------------------------------


def test_admin_creating_counsellor_tags_categories(admin_client, admin_user):
    """Report 3 §1.17: when admin creates a counsellor, the selected
    counselling categories are linked to the new CounsellorProfile."""
    from apps.accounts.models import ModuleRight, User
    from apps.accounts.services import get_or_create_default_roles
    from apps.counseling.models import CounselingCategory, CounsellorProfile

    # The counseling admin fixture only grants counseling perms; user creation
    # also needs accounts.add.
    ModuleRight.objects.get_or_create(role=admin_user.role, module="accounts", action="add")
    roles = get_or_create_default_roles()
    cat1 = CounselingCategory.objects.create(name="career")
    cat2 = CounselingCategory.objects.create(name="learning")

    resp = admin_client.post(
        "/api/accounts/users/",
        {
            "email": "newcounsellor@test.com",
            "full_name": "New Counsellor",
            "role": roles["counsellor"].id,
            "counsellor_categories": [cat1.id, cat2.id],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    user = User.objects.get(email="newcounsellor@test.com")
    profile = CounsellorProfile.objects.get(user=user)
    assert set(profile.categories.values_list("id", flat=True)) == {cat1.id, cat2.id}


# ---------------------------------------------------------------------------
# Report 3 §1.5 — avatar upload
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Report 3 1.5 - avatar upload
# ---------------------------------------------------------------------------


def test_user_can_upload_avatar(counselee_client, counselee_user):
    """Report 3 1.5: a user can upload their avatar via POST /api/me/avatar/."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    # 1x1 transparent PNG
    hex_png = (
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c63fcffff3f0300060002fea13581ea"
        "0000000049454e44ae426082"
    )
    upload = SimpleUploadedFile("avatar.png", bytes.fromhex(hex_png), content_type="image/png")
    resp = counselee_client.post("/api/me/avatar", {"avatar": upload}, format="multipart")
    assert resp.status_code == 200, resp.data
    counselee_user.refresh_from_db()
    assert bool(counselee_user.profile.avatar)


def test_avatar_requires_file(counselee_client):
    resp = counselee_client.post("/api/me/avatar", {}, format="multipart")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Report 3 §1.15/§1.16 — configurable refunds + reason + ownership on cancel
# ---------------------------------------------------------------------------


def test_cancel_requires_reason(counselee_client, counselee_user, counsellor_user):
    """Report 3 §1.16: a cancellation reason is required."""
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, hours_from_now=48)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="x",
        fee="100.00",
        status="confirmed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee"},
        format="json",
    )
    assert resp.status_code == 400


def test_unrelated_user_cannot_cancel(counselee_client, counsellor_user):
    """Only the counselee, the counsellor, or admin may cancel."""
    from apps.accounts.tests.factories import UserFactory

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, hours_from_now=48)
    from apps.accounts.services import get_or_create_default_roles

    other = UserFactory.create(
        role=get_or_create_default_roles()["individual"], email="other@test.com"
    )
    session = CounselingSession.objects.create(
        counselee=other,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="x",
        fee="100.00",
        status="confirmed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee", "reason": "x"},
        format="json",
    )
    # The session list is scoped to the counselee, so an unrelated user gets a
    # 404 (no existence leak) rather than a 403.
    assert resp.status_code == 404


def test_refund_thresholds_are_configurable(counselee_client, counselee_user, counsellor_user):
    """Report 3 §1.15: admin can change the refund thresholds; a 10h-before
    cancel earns a half refund when full_refund_within_hours is raised to 48."""
    from apps.counseling.models import CounselingSettings

    settings = CounselingSettings.get()
    settings.full_refund_within_hours = 48
    settings.save(update_fields=["full_refund_within_hours"])

    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor, hours_from_now=10)  # 10h: was full, now half
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="x",
        fee="100.00",
        status="confirmed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee", "reason": "conflict"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["data"]["cancellation"]["refund_tier"] == "half"


# ---------------------------------------------------------------------------
# Report 3 §1.3/§1.12 — maintenance command
# ---------------------------------------------------------------------------


def test_maintenance_auto_cancels_stale_pending(counselee_user, counsellor_user):
    """§1.12: a pending booking older than the confirm window is auto-cancelled
    and the counselee notified."""
    from datetime import timedelta

    from django.core.management import call_command
    from django.utils import timezone

    from apps.notifications.models import Notification

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, hours_from_now=48)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="x",
        fee="100.00",
        status="pending",
    )
    # booked_at is auto_now_add; force it into the past via a queryset update.
    CounselingSession.objects.filter(id=session.id).update(
        booked_at=timezone.now() - timedelta(hours=10)  # past the 6h window
    )
    call_command("counseling_maintenance", "--confirm", verbosity=0)
    session.refresh_from_db()
    assert session.status == "cancelled"
    timeslot.refresh_from_db()
    assert timeslot.status == "available"
    assert Notification.objects.filter(recipient=counselee_user, title__contains="expired").exists()


def test_maintenance_notifies_slot_shortage(counsellor_user):
    """§1.3: a counsellor with no near-term available slots is notified."""
    from django.core.management import call_command

    from apps.notifications.models import Notification

    _make_counsellor(counsellor_user)  # no near-term slots -> shortage
    call_command("counseling_maintenance", "--slots", verbosity=0)
    assert Notification.objects.filter(
        recipient=counsellor_user, title__contains="Timeslot update"
    ).exists()


# ---------------------------------------------------------------------------
# H15 — payment gateway wiring (D8 §2.1/§3.3): booking + follow-up must NOT
# assume payment is done; only the gateway/webhook can mark a session paid.
# ---------------------------------------------------------------------------


def test_booking_does_not_auto_pay_without_gateway(
    counselee_client, counselee_user, counsellor_user
):
    """A paid session stays payment_status='pending' after booking — it only
    becomes 'paid' via the payments webhook (Stripe not configured in tests,
    so create_stripe_checkout_session returns None and checkout_url is null,
    matching the 'manual processing' branch used by training)."""
    from apps.payments.models import Payment

    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor)
    resp = counselee_client.post(
        "/api/counseling/sessions/",
        {
            "counsellor": counsellor.id,
            "timeslot": timeslot.id,
            "topic": "Career advice",
            "terms_accepted": True,
            "mode": "online",
        },
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["payment_status"] == "pending"
    assert "checkout_url" in resp.data["data"]

    session = CounselingSession.objects.get(id=resp.data["data"]["id"])
    assert session.payment_status == "pending"

    # A Payment record was created for this booking, also pending.
    payment = Payment.objects.get(module="counseling", item_id=session.id, user=counselee_user)
    assert payment.status == "pending"
    assert float(payment.amount) == 100.0


def test_free_session_booking_is_auto_paid(counselee_client, counselee_user, counsellor_user):
    """A zero-fee session (counsellor hourly_rate=0) needs no gateway — it's
    auto-paid immediately, same as a free training course."""
    counsellor = _make_counsellor(counsellor_user, hourly_rate="0.00")
    timeslot = _make_timeslot(counsellor)
    resp = counselee_client.post(
        "/api/counseling/sessions/",
        {
            "counsellor": counsellor.id,
            "timeslot": timeslot.id,
            "topic": "Free session",
            "terms_accepted": True,
            "mode": "online",
        },
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["payment_status"] == "paid"
    assert resp.data["data"]["checkout_url"] is None


def test_followup_confirm_does_not_auto_pay(counselee_client, counselee_user, counsellor_user):
    """H15: confirming a follow-up must no longer hardcode payment_status='paid'
    ('Assume payment done') — it goes through the same gateway wiring as booking."""
    from apps.counseling.models import FollowupSession
    from apps.payments.models import Payment

    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="completed",
    )
    followup = FollowupSession.objects.create(
        original_session=session,
        counsellor=counsellor,
        proposed_time="2026-08-15T10:00:00Z",
        status="proposed",
    )
    resp = counselee_client.post(f"/api/counseling/followups/{followup.id}/confirm/")
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["session"]["payment_status"] == "pending"
    assert "checkout_url" in resp.data["data"]

    new_session = CounselingSession.objects.get(id=resp.data["data"]["session"]["id"])
    assert new_session.payment_status == "pending"
    assert Payment.objects.filter(
        module="counseling", item_id=new_session.id, user=counselee_user, status="pending"
    ).exists()


def test_webhook_marks_counseling_session_paid(counselee_client, counselee_user, counsellor_user):
    """The payments webhook (apps/payments/services._update_module_payment_status)
    is what actually flips a counselling session to 'paid' — never the view."""
    from apps.payments.models import Payment
    from apps.payments.services import _update_module_payment_status

    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee="100.00",
        status="pending",
        payment_status="pending",
    )
    payment = Payment.objects.create(
        user=counselee_user,
        module="counseling",
        item_id=session.id,
        amount="100.00",
        status="paid",
    )
    _update_module_payment_status(payment)
    session.refresh_from_db()
    assert session.payment_status == "paid"


# ---------------------------------------------------------------------------
# H16 — per-session meeting link (D8 §2.3 live-delivery layer)
# ---------------------------------------------------------------------------


def test_counsellor_sets_meeting_link(counsellor_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="confirmed",
    )
    resp = counsellor_client.post(
        f"/api/counseling/sessions/{session.id}/meeting-link/",
        {"meeting_link": "https://zoom.us/j/123456789"},
        format="json",
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["meeting_link"] == "https://zoom.us/j/123456789"
    session.refresh_from_db()
    assert session.meeting_link == "https://zoom.us/j/123456789"


def test_counselee_cannot_set_meeting_link(counselee_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor)
    session = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=timeslot,
        topic="Test",
        fee=counsellor.hourly_rate,
        status="confirmed",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/meeting-link/",
        {"meeting_link": "https://zoom.us/j/hijacked"},
        format="json",
    )
    assert resp.status_code == 403, f"Got {resp.status_code}: {resp.data}"
    session.refresh_from_db()
    assert session.meeting_link == ""
