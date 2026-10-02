"""Report 9 #76: individuals (and any non-author role) see only PUBLISHED
profiling solutions; the authors (CJ Admin, Psychometrician) see every status."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.career_profiling.models import ProfilingSolution

pytestmark = pytest.mark.django_db


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _user(role_name, email):
    roles = get_or_create_default_roles()
    role = roles[role_name]
    ModuleRight.objects.get_or_create(role=role, module="career_profiling", action="view")
    return UserFactory(role=role, email=email)


@pytest.fixture
def solutions(db):
    return {
        status: ProfilingSolution.objects.create(
            title=f"{status} solution", status=status, description="<p>About</p>"
        )
        for status in ("draft", "published", "archived")
    }


def _titles(resp):
    return {s["title"] for s in resp.data["data"]["results"]}


def test_individual_lists_only_published_solutions(solutions):
    resp = _client(_user("individual", "ind@test.com")).get("/api/career-profiling/solutions/")
    assert resp.status_code == 200
    assert _titles(resp) == {"published solution"}
    # The candidate view shows the description (and image) of each solution.
    row = resp.data["data"]["results"][0]
    assert row["description"] == "<p>About</p>"
    assert "image" in row


def test_individual_cannot_open_unpublished_solutions(solutions):
    client = _client(_user("individual", "ind@test.com"))
    base = "/api/career-profiling/solutions"
    assert client.get(f"{base}/{solutions['draft'].id}/").status_code == 404
    assert client.get(f"{base}/{solutions['archived'].id}/").status_code == 404
    assert client.get(f"{base}/{solutions['published'].id}/").status_code == 200


@pytest.mark.parametrize("role_name", ["cj_admin", "psychometrician"])
def test_authors_keep_every_status(solutions, role_name):
    resp = _client(_user(role_name, f"{role_name}@test.com")).get(
        "/api/career-profiling/solutions/"
    )
    assert resp.status_code == 200
    assert _titles(resp) == {"draft solution", "published solution", "archived solution"}


def test_candidate_sees_only_own_match_indices(solutions):
    """Report 9 review: individuals hold profiling 'view' — match indices of
    other candidates must not be listed to them."""
    from apps.career_profiling.models import MatchIndex

    me = _user("individual", "me@t.com")
    other = _user("individual", "other@t.com")
    sol = solutions["published"]
    MatchIndex.objects.create(solution=sol, candidate=me, career_title="Mine")
    MatchIndex.objects.create(solution=sol, candidate=other, career_title="Theirs")
    resp = _client(me).get(f"/api/career-profiling/solutions/{sol.id}/match_indices/")
    assert resp.status_code == 200, resp.data
    assert {r["career_title"] for r in resp.data["data"]} == {"Mine"}
