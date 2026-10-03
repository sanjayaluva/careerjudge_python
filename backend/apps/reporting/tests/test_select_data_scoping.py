"""Code review: ``select_data`` must not leak another candidate's HFMI/LFMI."""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.career_profiling.models import ProfilingSolution
from apps.reporting.models import Report
from apps.reporting.tests.test_group_and_hfmi import _make_match_index, _make_user

pytestmark = pytest.mark.django_db


def _client(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def psychometrician_user(roles):
    role = roles["psychometrician"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="reporting", action=action)
    return UserFactory(role=role, email="psy@test.com")


@pytest.fixture
def psy_client(psychometrician_user):
    return _client(psychometrician_user)


@pytest.fixture
def profiling_report(psychometrician_user):
    solution = ProfilingSolution.objects.create(
        title="S", status="published", created_by=psychometrician_user
    )
    return Report.objects.create(
        title="Profiling",
        report_type="descriptive",
        scope="profiling",
        profiling_solution=solution,
        status="published",
        created_by=psychometrician_user,
    )


def _select(client, report, candidate_id):
    return client.post(
        f"/api/reporting/reports/{report.id}/select_data/",
        {
            "candidate_id": candidate_id,
            "data_type": "HFMI",
            "extraction_mode": "system",
            "n_categories": 1,
            "n_criterions": 2,
        },
        format="json",
    )


def test_individual_cannot_select_another_candidates_match_indices(profiling_report, roles):
    victim = _make_user("victim@test.com")
    _make_match_index(profiling_report.profiling_solution, victim, "IT", "Prog", "ITP", 95.0)
    attacker = _make_user("attacker@test.com")
    ModuleRight.objects.get_or_create(role=roles["individual"], module="reporting", action="view")
    r = _select(_client(attacker), profiling_report, victim.id)
    assert r.status_code == 404


def test_individual_selects_his_own_match_indices(profiling_report, roles):
    me = _make_user("me@test.com")
    _make_match_index(profiling_report.profiling_solution, me, "IT", "Prog", "ITP", 95.0)
    ModuleRight.objects.get_or_create(role=roles["individual"], module="reporting", action="view")
    r = _select(_client(me), profiling_report, me.id)
    assert r.status_code == 200, r.data
    assert [c["career_title"] for c in r.data["data"]["selected"]] == ["Prog"]


def test_psychometrician_selects_any_candidate(profiling_report, psy_client):
    cand = _make_user("cand@test.com")
    _make_match_index(profiling_report.profiling_solution, cand, "IT", "Prog", "ITP", 95.0)
    r = _select(psy_client, profiling_report, cand.id)
    assert r.status_code == 200, r.data
    assert [c["career_title"] for c in r.data["data"]["selected"]] == ["Prog"]
