"""Report 9 #105: CJ Admin adds, edits and deletes the counselling ("domain")
categories used to tag counsellors. They used to be fixed in code."""

import importlib

import pytest
from django.apps import apps as django_apps

from apps.counseling.models import CounselingCategory, CounselingSession

from . import test_counseling as base

# Fixtures and helpers shared with the main counselling tests.
roles = base.roles
admin_user = base.admin_user
admin_client = base.admin_client
counselee_user = base.counselee_user
counselee_client = base.counselee_client
counsellor_user = base.counsellor_user
_make_counsellor = base._make_counsellor
_make_timeslot = base._make_timeslot

pytestmark = pytest.mark.django_db

URL = "/api/counseling/categories/"


def _codes(resp):
    return {c["name"] for c in resp.data["data"]}


def test_migration_keeps_existing_rows_and_creates_the_seven_defaults():
    """The data migration labels existing rows in place (same id/code, so
    tags survive) and creates the Doc 8 categories that are missing."""
    migration = importlib.import_module(
        "apps.counseling.migrations.0008_categories_managed_by_admin"
    )
    CounselingCategory.objects.all().delete()
    kept = CounselingCategory.objects.create(name="career")
    custom = CounselingCategory.objects.create(name="Career")
    migration.seed_categories(django_apps, None)
    kept.refresh_from_db()
    custom.refresh_from_db()
    assert kept.label == "Career counselling"
    assert custom.label == "Career"
    assert CounselingCategory.objects.count() == 8
    assert CounselingCategory.objects.get(name="health").label == "Health counselling"


def test_admin_adds_renames_and_deactivates(admin_client, counselee_client):
    created = admin_client.post(URL, {"label": "Parenting"}, format="json")
    assert created.status_code == 201, created.data
    cat_id = created.data["data"]["id"]
    assert created.data["data"]["name"] == "parenting"
    # Same name twice (any case) is refused.
    assert admin_client.post(URL, {"label": "parenting"}, format="json").status_code == 400

    renamed = admin_client.patch(f"{URL}{cat_id}/", {"label": "Parenting support"}, format="json")
    assert renamed.status_code == 200, renamed.data
    assert renamed.data["data"]["label"] == "Parenting support"
    # The code is fixed once created.
    bad = admin_client.patch(f"{URL}{cat_id}/", {"name": "other"}, format="json")
    assert bad.status_code == 400

    assert "parenting" in _codes(counselee_client.get(URL))
    off = admin_client.patch(f"{URL}{cat_id}/", {"is_active": False}, format="json")
    assert off.status_code == 200
    # Hidden from everyone else's list; CJ Admin still sees (and can revive) it.
    assert "parenting" not in _codes(counselee_client.get(URL))
    assert "parenting" in _codes(admin_client.get(URL))
    assert "parenting" not in _codes(admin_client.get(f"{URL}?active=true"))


def test_only_cj_admin_manages_categories(counselee_client, counsellor_user):
    from rest_framework.test import APIClient

    assert counselee_client.post(URL, {"label": "X"}, format="json").status_code == 403
    career = CounselingCategory.objects.get(name="career")
    assert counselee_client.patch(f"{URL}{career.id}/", {"label": "Y"}).status_code == 403
    assert counselee_client.delete(f"{URL}{career.id}/").status_code == 403
    # The counsellor holds counselling 'delete' but is not CJ Admin.
    c = APIClient()
    c.force_authenticate(counsellor_user)
    assert c.delete(f"{URL}{career.id}/").status_code == 403
    assert CounselingCategory.objects.filter(id=career.id).exists()


def test_delete_refused_while_in_use(admin_client, counsellor_user, counselee_user):
    unused = CounselingCategory.objects.create(name="spare", label="Spare")
    assert admin_client.delete(f"{URL}{unused.id}/").status_code == 200
    assert not CounselingCategory.objects.filter(id=unused.id).exists()

    tagged = CounselingCategory.objects.get(name="career")
    counsellor = _make_counsellor(counsellor_user)
    counsellor.categories.add(tagged)
    resp = admin_client.delete(f"{URL}{tagged.id}/")
    assert resp.status_code == 409
    assert "Deactivate" in resp.data["error"]["message"]

    booked = CounselingCategory.objects.get(name="learning")
    CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        category=booked,
        timeslot=_make_timeslot(counsellor),
        topic="t",
    )
    listed = {c["name"]: c for c in admin_client.get(URL).data["data"]}
    assert listed["learning"]["session_count"] == 1
    assert listed["career"]["counsellor_count"] == 1
    assert admin_client.delete(f"{URL}{booked.id}/").status_code == 409


def test_tagging_and_filter_use_the_live_list(admin_client, counselee_client, counsellor_user):
    counsellor = _make_counsellor(counsellor_user)
    new = CounselingCategory.objects.create(name="parenting", label="Parenting")
    url = f"/api/counseling/counsellors/{counsellor.id}/set-categories/"
    resp = admin_client.post(url, {"categories": [new.id, "career"]}, format="json")
    assert resp.status_code == 200, resp.data
    assert sorted(resp.data["data"]["category_names"]) == ["Career counselling", "Parenting"]

    listed = counselee_client.get(f"/api/counseling/counsellors/?category={new.id}")
    assert [c["id"] for c in listed.data["data"]["results"]] == [counsellor.id]

    # Renaming shows everywhere; deactivating keeps the existing tag...
    new.label, new.is_active = "Parenting help", False
    new.save()
    keep = admin_client.post(url, {"categories": [new.id]}, format="json")
    assert keep.status_code == 200
    assert keep.data["data"]["category_names"] == ["Parenting help"]
    # ...but it cannot be given to another counsellor.
    other = _make_counsellor(_another_counsellor(counsellor_user))
    other_url = f"/api/counseling/counsellors/{other.id}/set-categories/"
    assert admin_client.post(other_url, {"categories": [new.id]}, format="json").status_code == 400


def _another_counsellor(user):
    from apps.accounts.tests.factories import UserFactory

    return UserFactory(role=user.role, email="second.counsellor@test.com")


def test_inactive_category_hidden_from_new_bookings(
    counselee_client, counselee_user, counsellor_user
):
    counsellor = _make_counsellor(counsellor_user)
    old = CounselingCategory.objects.get(name="clinical")
    existing = CounselingSession.objects.create(
        counselee=counselee_user,
        counsellor=counsellor,
        category=old,
        timeslot=_make_timeslot(counsellor, hours_from_now=72),
        topic="Earlier",
    )
    old.is_active = False
    old.save()
    slot = _make_timeslot(counsellor)
    body = {
        "counsellor": counsellor.id,
        "timeslot": slot.id,
        "topic": "Help",
        "terms_accepted": True,
        "category": old.id,
    }
    refused = counselee_client.post("/api/counseling/sessions/", body, format="json")
    assert refused.status_code == 400
    # The existing session still shows its category.
    shown = counselee_client.get(f"/api/counseling/sessions/{existing.id}/")
    assert shown.data["data"]["category_name"] == "Clinical problems"
    body["category"] = CounselingCategory.objects.get(name="career").id
    ok = counselee_client.post("/api/counseling/sessions/", body, format="json")
    assert ok.status_code == 201, ok.data
    assert ok.data["data"]["category_name"] == "Career counselling"


def test_booking_service_refuses_inactive_category(counselee_user, counsellor_user):
    from apps.counseling.services import BookingError, book_session

    counsellor = _make_counsellor(counsellor_user)
    inactive = CounselingCategory.objects.create(name="old", label="Old", is_active=False)
    with pytest.raises(BookingError):
        book_session(
            counselee=counselee_user,
            counsellor=counsellor,
            timeslot=_make_timeslot(counsellor),
            topic="t",
            category=inactive,
        )
