"""Report 9 #115: Help Desk views ALL booked counselling sessions (read-only
"All booked sessions" list on the Counseling page)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.counseling.models import CounselingCategory, CounselingSession

from .test_counseling import _make_counsellor, _make_timeslot

pytestmark = pytest.mark.django_db


def test_helpdesk_lists_every_booked_session_with_list_columns():
    roles = get_or_create_default_roles()
    ModuleRight.objects.get_or_create(role=roles["helpdesk"], module="counseling", action="view")
    helpdesk = UserFactory(role=roles["helpdesk"], email="helpdesk@test.com")
    category = CounselingCategory.objects.create(name="Career")
    for i in range(2):
        counsellor = _make_counsellor(
            UserFactory(role=roles["counsellor"], email=f"c{i}@test.com"), full_name=f"Dr. {i}"
        )
        CounselingSession.objects.create(
            counselee=UserFactory(role=roles["individual"], email=f"u{i}@test.com"),
            counsellor=counsellor,
            category=category,
            timeslot=_make_timeslot(counsellor),
            topic=f"Topic {i}",
            fee=counsellor.hourly_rate,
        )

    client = APIClient()
    client.force_authenticate(user=helpdesk)
    resp = client.get("/api/counseling/sessions/")
    assert resp.status_code == 200
    rows = resp.data["data"]["results"]
    assert {r["topic"] for r in rows} == {"Topic 0", "Topic 1"}
    # Columns the Help Desk list shows: counsellor, counselee, date/time,
    # status and category.
    for r in rows:
        assert r["counsellor_name"].startswith("Dr. ")
        assert r["counselee_email"].endswith("@test.com")
        assert r["timeslot_detail"]["start_time"]
        assert r["status"] == "pending"
        assert r["category_name"] == "Career"
