"""Tests for the dossier "medium" counseling gaps (D8):

  - Session start/end split + third-party redirect: the `join` action
    enforces the join window server-side, records `actual_start_at` on
    first join, and returns the per-session meeting_link to redirect to;
    `complete` records the matching `actual_end_at`.
  - Browse future weeks: `counsellors/<id>/timeslots/?week_offset=N` returns
    just that one calendar week's slots (0 = this week, 1 = next, ...).
  - Refund execution: a cancellation's refund is executed against the
    payments module (Payment record flipped to 'refunded'), not just
    recorded on SessionCancellation.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.counseling.models import CounselingSession, CounsellorProfile, TimeSlot
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def counsellor_user(db, roles):
    role = roles["counsellor"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="counseling", action=action)
    return UserFactory(role=role, email="dg_counsellor@test.com")


@pytest.fixture
def counselee_user(db, roles):
    role = roles["individual"]
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(role=role, module="counseling", action=action)
    return UserFactory(role=role, email="dg_counselee@test.com")


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


def _make_counsellor(user, hourly_rate=100):
    from apps.accounts.models import UserProfile

    up, _ = UserProfile.objects.get_or_create(user=user)
    up.hourly_rate = hourly_rate
    up.is_available_for_counseling = True
    up.save()
    user.full_name = "Dr. Test"
    user.save()
    return CounsellorProfile.objects.create(user=user)


def _make_timeslot(counsellor, hours_from_now=0.0, **overrides):
    start = timezone.now() + timedelta(hours=hours_from_now)
    defaults = {
        "counsellor": counsellor,
        "start_time": start,
        "end_time": start + timedelta(hours=1),
        "status": "available",
    }
    defaults.update(overrides)
    return TimeSlot.objects.create(**defaults)


def _make_session(counselee, counsellor, timeslot, **overrides):
    defaults = {
        "counselee": counselee,
        "counsellor": counsellor,
        "timeslot": timeslot,
        "topic": "Test",
        "fee": counsellor.hourly_rate,
        "status": "confirmed",
        "mode": "online",
    }
    defaults.update(overrides)
    return CounselingSession.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Session start/end split + join-window redirect (D8)
# ---------------------------------------------------------------------------


def test_join_within_window_records_actual_start_and_returns_link(
    counselee_client, counselee_user, counsellor_user
):
    counsellor = _make_counsellor(counsellor_user)
    # Starts in 5 minutes -> inside the 10-minute-before join window.
    timeslot = _make_timeslot(counsellor, hours_from_now=5 / 60)
    session = _make_session(
        counselee_user, counsellor, timeslot, meeting_link="https://zoom.us/j/1"
    )
    resp = counselee_client.post(f"/api/counseling/sessions/{session.id}/join/")
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["meeting_link"] == "https://zoom.us/j/1"
    session.refresh_from_db()
    assert session.actual_start_at is not None


def test_join_before_window_opens_is_forbidden(counselee_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    # Starts in 2 hours -> well outside the 10-minute join window.
    timeslot = _make_timeslot(counsellor, hours_from_now=2)
    session = _make_session(
        counselee_user, counsellor, timeslot, meeting_link="https://zoom.us/j/1"
    )
    resp = counselee_client.post(f"/api/counseling/sessions/{session.id}/join/")
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "join_window_closed"
    session.refresh_from_db()
    assert session.actual_start_at is None


def test_join_requires_meeting_link(counselee_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, hours_from_now=0)
    session = _make_session(counselee_user, counsellor, timeslot, meeting_link="")
    resp = counselee_client.post(f"/api/counseling/sessions/{session.id}/join/")
    assert resp.status_code == 400
    assert resp.data["error"]["code"] == "not_ready"


def test_unrelated_user_cannot_join(counselee_user, counsellor_user, roles):
    """The session list is scoped to its counselee/counsellor, so an
    unrelated user gets a 404 (no existence leak) rather than a 403 —
    same convention as cancel() (see test_unrelated_user_cannot_cancel)."""
    from rest_framework_simplejwt.tokens import RefreshToken

    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, hours_from_now=0)
    session = _make_session(
        counselee_user, counsellor, timeslot, meeting_link="https://zoom.us/j/1"
    )
    other_role = roles["individual"]
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(role=other_role, module="counseling", action=action)
    other = UserFactory(role=other_role, email="dg_other@test.com")
    client = APIClient()
    refresh = RefreshToken.for_user(other)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    resp = client.post(f"/api/counseling/sessions/{session.id}/join/")
    assert resp.status_code == 404


def test_complete_records_actual_end_at(counsellor_client, counselee_user, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    timeslot = _make_timeslot(counsellor, hours_from_now=0)
    session = _make_session(counselee_user, counsellor, timeslot)
    resp = counsellor_client.post(f"/api/counseling/sessions/{session.id}/complete/")
    assert resp.status_code == 200
    session.refresh_from_db()
    assert session.completed_at is not None
    assert session.actual_end_at is not None
    assert session.actual_end_at == session.completed_at


# ---------------------------------------------------------------------------
# Browse future weeks (D8)
# ---------------------------------------------------------------------------


def test_browse_future_week_offset_returns_only_that_week(counselee_client, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    this_week_slot = _make_timeslot(counsellor, hours_from_now=1)
    next_week_slot = _make_timeslot(counsellor, hours_from_now=24 * 8)
    week_after_slot = _make_timeslot(counsellor, hours_from_now=24 * 15)

    resp0 = counselee_client.get(
        f"/api/counseling/counsellors/{counsellor.id}/timeslots/?week_offset=0"
    )
    assert resp0.status_code == 200
    ids0 = [s["id"] for s in resp0.data["data"]]
    assert ids0 == [this_week_slot.id]

    resp1 = counselee_client.get(
        f"/api/counseling/counsellors/{counsellor.id}/timeslots/?week_offset=1"
    )
    ids1 = [s["id"] for s in resp1.data["data"]]
    assert ids1 == [next_week_slot.id]

    resp2 = counselee_client.get(
        f"/api/counseling/counsellors/{counsellor.id}/timeslots/?week_offset=2"
    )
    ids2 = [s["id"] for s in resp2.data["data"]]
    assert ids2 == [week_after_slot.id]


def test_browse_future_week_offset_capped_at_max_weeks_ahead(counselee_client, counsellor_user):
    from apps.counseling.models import CounselingSettings

    CounselingSettings.get()  # ensure singleton exists (default max_weeks_ahead=3)
    counsellor = _make_counsellor(counsellor_user)
    resp = counselee_client.get(
        f"/api/counseling/counsellors/{counsellor.id}/timeslots/?week_offset=99"
    )
    assert resp.status_code == 200  # capped, not rejected


def test_browse_future_week_offset_rejects_non_integer(counselee_client, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    resp = counselee_client.get(
        f"/api/counseling/counsellors/{counsellor.id}/timeslots/?week_offset=abc"
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Refund execution (D8)
# ---------------------------------------------------------------------------


def test_cancellation_executes_refund_against_payment_record(
    counselee_client, counselee_user, counsellor_user
):
    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor, hours_from_now=48)
    session = _make_session(counselee_user, counsellor, timeslot, fee="100.00")
    payment = Payment.objects.create(
        user=counselee_user,
        module="counseling",
        item_id=session.id,
        amount="100.00",
        status="paid",
        provider="manual",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee", "reason": "Schedule conflict"},
        format="json",
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["cancellation"]["refund_executed"] is True
    payment.refresh_from_db()
    assert payment.status == "refunded"
    assert payment.refunded_at is not None


def test_cancellation_with_no_refund_does_not_mark_payment_refunded(
    counselee_client, counselee_user, counsellor_user
):
    """<4h before → no refund tier → the payment is left untouched."""
    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor, hours_from_now=1)
    session = _make_session(counselee_user, counsellor, timeslot, fee="100.00")
    payment = Payment.objects.create(
        user=counselee_user,
        module="counseling",
        item_id=session.id,
        amount="100.00",
        status="paid",
        provider="manual",
    )
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee", "reason": "Last minute"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["data"]["cancellation"]["refund_tier"] == "none"
    assert resp.data["data"]["cancellation"]["refund_executed"] is False
    payment.refresh_from_db()
    assert payment.status == "paid"


def test_cancellation_without_payment_record_records_but_does_not_execute(
    counselee_client, counselee_user, counsellor_user
):
    """No Payment row on file (e.g. legacy/manual booking) — cancellation
    still succeeds, refund_executed just stays False."""
    counsellor = _make_counsellor(counsellor_user, hourly_rate="100.00")
    timeslot = _make_timeslot(counsellor, hours_from_now=48)
    session = _make_session(counselee_user, counsellor, timeslot, fee="100.00")
    resp = counselee_client.post(
        f"/api/counseling/sessions/{session.id}/cancel/",
        {"cancelled_by": "counselee", "reason": "Schedule conflict"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["data"]["cancellation"]["refund_executed"] is False
