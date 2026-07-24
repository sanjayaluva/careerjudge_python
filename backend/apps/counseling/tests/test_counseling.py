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
        {"counsellor": counsellor.id, "timeslot": timeslot.id, "topic": "Test"},
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
        {"cancelled_by": "counselee"},
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
        {"cancelled_by": "counselee"},
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
