"""Code review fixes — counselling: cancelled slots, follow-up scoping, and
session fields that must not change after booking."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.counseling.models import (
    CounselingSession,
    FollowupSession,
    SessionCancellation,
    TimeSlot,
)
from apps.counseling.tests.test_counseling import _make_counsellor, _make_timeslot

pytestmark = pytest.mark.django_db


def _client(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def counsellor_user(roles):
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(
            role=roles["counsellor"], module="counseling", action=action
        )
    return UserFactory(role=roles["counsellor"], email="counsellor@test.com")


@pytest.fixture
def counselee_user(roles):
    return _individual(roles, "counselee@test.com")


@pytest.fixture
def counsellor_client(counsellor_user):
    return _client(counsellor_user)


@pytest.fixture
def counselee_client(counselee_user):
    return _client(counselee_user)


def _book(client, counsellor, slot):
    return client.post(
        "/api/counseling/sessions/",
        {
            "counsellor": counsellor.id,
            "timeslot": slot.id,
            "topic": "t",
            "mode": "online",
            "terms_accepted": True,
        },
        format="json",
    )


def _individual(roles, email):
    for action in ("view", "add", "change"):
        ModuleRight.objects.get_or_create(
            role=roles["individual"], module="counseling", action=action
        )
    return UserFactory(role=roles["individual"], email=email)


# --- Cancelled slot: rebookable time, protected history ---------------------


def test_cancelled_session_time_can_be_rebooked(
    counselee_client, counsellor_user, counsellor_client, roles
):
    counsellor = _make_counsellor(counsellor_user, hourly_rate=0)
    slot = _make_timeslot(counsellor)
    sid = _book(counselee_client, counsellor, slot).data["data"]["id"]
    r = counselee_client.post(
        f"/api/counseling/sessions/{sid}/cancel/", {"reason": "busy"}, format="json"
    )
    assert r.status_code == 200, r.data

    # The listed available slot at that time is a fresh one with no session.
    r = counselee_client.get(f"/api/counseling/counsellors/{counsellor.id}/timeslots/")
    listed = [s for s in r.data["data"] if s["status"] == "available"]
    assert len(listed) == 1 and listed[0]["id"] != slot.id

    other = _individual(roles, "other@test.com")
    r = _book(_client(other), counsellor, TimeSlot.objects.get(id=listed[0]["id"]))
    assert r.status_code == 201, r.data

    # The counsellor's own list doesn't show the cancelled slot either.
    r = counsellor_client.get(f"/api/counseling/timeslots/?counsellor={counsellor.id}")
    rows = r.data["results"] if isinstance(r.data, dict) and "results" in r.data else r.data
    assert slot.id not in [s["id"] for s in rows]


def test_slot_holding_a_cancelled_session_cannot_be_deleted(
    counselee_client, counsellor_user, counsellor_client
):
    counsellor = _make_counsellor(counsellor_user, hourly_rate=0)
    slot = _make_timeslot(counsellor)
    sid = _book(counselee_client, counsellor, slot).data["data"]["id"]
    counselee_client.post(
        f"/api/counseling/sessions/{sid}/cancel/", {"reason": "busy"}, format="json"
    )
    r = counsellor_client.delete(f"/api/counseling/timeslots/{slot.id}/")
    assert r.status_code == 403
    assert CounselingSession.objects.filter(id=sid).exists()
    assert SessionCancellation.objects.filter(session_id=sid).exists()


def test_legacy_available_slot_with_a_session_is_not_listed(counselee_user, counsellor_user):
    """Slots freed by the old cancel code (status 'available' but still
    holding the cancelled session) must not be offered."""
    counsellor = _make_counsellor(counsellor_user, hourly_rate=0)
    slot = _make_timeslot(counsellor)
    CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        timeslot=slot,
        topic="t",
        status="cancelled",
    )
    r = _client(counselee_user).get(f"/api/counseling/counsellors/{counsellor.id}/timeslots/")
    assert slot.id not in [s["id"] for s in r.data["data"]]


# --- Follow-ups: scoped list, counselee-only confirm/decline -----------------


@pytest.fixture
def followup(counselee_client, counsellor_user):
    counsellor = _make_counsellor(counsellor_user, hourly_rate=0)
    slot = _make_timeslot(counsellor)
    sid = _book(counselee_client, counsellor, slot).data["data"]["id"]
    return FollowupSession.objects.create(
        original_session_id=sid,
        counsellor=counsellor,
        proposed_time=timezone.now() + timedelta(days=5),
        status="proposed",
    )


def _ids(resp):
    data = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
    return [row["id"] for row in data]


def test_stranger_cannot_list_or_decline_a_followup(followup, roles):
    stranger = _client(_individual(roles, "stranger@test.com"))
    r = stranger.get("/api/counseling/followups/")
    assert r.status_code == 200
    assert followup.id not in _ids(r)
    r = stranger.post(f"/api/counseling/followups/{followup.id}/decline/", format="json")
    assert r.status_code == 404
    followup.refresh_from_db()
    assert followup.status == "proposed"


def test_counsellor_sees_but_cannot_decline_his_followup(followup, counsellor_client):
    r = counsellor_client.get("/api/counseling/followups/")
    assert followup.id in _ids(r)
    r = counsellor_client.post(f"/api/counseling/followups/{followup.id}/decline/", format="json")
    assert r.status_code == 403
    followup.refresh_from_db()
    assert followup.status == "proposed"


def test_counselee_declines_his_followup(followup, counselee_client):
    r = counselee_client.post(f"/api/counseling/followups/{followup.id}/decline/", format="json")
    assert r.status_code == 200, r.data
    followup.refresh_from_db()
    assert followup.status == "declined"


def test_followup_cannot_be_confirmed_by_patch_or_created_directly(
    followup, counselee_client, counselee_user
):
    r = counselee_client.patch(
        f"/api/counseling/followups/{followup.id}/", {"status": "confirmed"}, format="json"
    )
    assert r.status_code == 405
    followup.refresh_from_db()
    assert followup.status == "proposed"
    r = counselee_client.post(
        "/api/counseling/followups/",
        {
            "original_session": followup.original_session_id,
            "counsellor": followup.counsellor_id,
            "proposed_time": (timezone.now() + timedelta(days=9)).isoformat(),
            "status": "confirmed",
        },
        format="json",
    )
    assert r.status_code == 405
    assert FollowupSession.objects.count() == 1


# --- Session PATCH cannot move the session ----------------------------------


def test_patch_cannot_move_a_session_to_another_slot(counselee_client, counsellor_user):
    counsellor = _make_counsellor(counsellor_user, hourly_rate=0)
    slot1 = _make_timeslot(counsellor)
    slot2 = _make_timeslot(counsellor, hours_from_now=72)
    sid = _book(counselee_client, counsellor, slot1).data["data"]["id"]
    counselee_client.patch(
        f"/api/counseling/sessions/{sid}/", {"timeslot": slot2.id, "topic": "new"}, format="json"
    )
    session = CounselingSession.objects.get(id=sid)
    assert session.timeslot_id == slot1.id
    assert session.topic == "new"  # other fields stay editable
    slot2.refresh_from_db()
    assert slot2.status == "available"


def test_counselee_cannot_propose_his_own_followup(followup, counselee_client, counsellor_client):
    """Verification pass: only the session's counsellor proposes follow-ups."""
    sid = followup.original_session_id
    when = (timezone.now() + timedelta(days=9)).isoformat()
    r = counselee_client.post(
        f"/api/counseling/sessions/{sid}/followups/", {"proposed_time": when}, format="json"
    )
    assert r.status_code == 403
    r = counsellor_client.post(
        f"/api/counseling/sessions/{sid}/followups/", {"proposed_time": when}, format="json"
    )
    assert r.status_code == 201, r.data


def test_confirming_a_followup_reuses_the_counsellors_open_slot(followup, counselee_client):
    """Verification pass: the counsellor usually proposes a time he already
    has open — confirming must book that slot, not crash on the one-live-slot
    rule."""
    open_slot = TimeSlot.objects.create(
        counsellor=followup.counsellor,
        start_time=followup.proposed_time,
        end_time=followup.proposed_time + timedelta(hours=1),
        status="available",
    )
    r = counselee_client.post(f"/api/counseling/followups/{followup.id}/confirm/", format="json")
    assert r.status_code in (200, 201), r.data
    open_slot.refresh_from_db()
    assert open_slot.status == "booked"
    assert CounselingSession.objects.filter(timeslot=open_slot).exists()


def test_empty_media_file_range_is_unsatisfiable(settings):
    from core.media import _byte_range

    assert _byte_range("bytes=-5", 0) is False
    assert _byte_range("bytes=0-", 0) is False
    assert _byte_range("bytes=-5", 10) == (5, 9)
