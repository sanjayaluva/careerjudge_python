"""Tests for the Career Profiling API endpoints.

Focus: POST /api/career-profiling/solutions/<id>/compute/ — the trigger
that runs the engine and persists MatchIndex records.

Auth matrix:
  - cj_admin / psychometrician: may pass `candidate_id` to compute for anyone
  - Other roles: candidate_id is ignored; computes for the authenticated user
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import (
    Assessment,
    AssessmentSection,
    AssessmentSession,
    SectionScore,
)
from apps.career_profiling.models import (
    Band,
    BandDefinition,
    MappingCriterion,
    MatchIndex,
    ProfilingSolution,
    SelectedAssessment,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def psychometrician_user(db, roles):
    role = roles["psychometrician"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="career_profiling", action=action)
    return UserFactory(role=role, email="psy@test.com")


@pytest.fixture
def individual_user(db, roles):
    """An 'individual' role user — has view-only rights on career_profiling."""
    role = roles["individual"]
    ModuleRight.objects.get_or_create(role=role, module="career_profiling", action="view")
    return UserFactory(role=role, email="individual@test.com")


@pytest.fixture
def psy_client(db, psychometrician_user):
    c = APIClient()
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(psychometrician_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def individual_client(db, individual_user):
    c = APIClient()
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(individual_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# Helpers — kept minimal (full engine coverage is in test_engine.py)
# ---------------------------------------------------------------------------


def _make_solution_with_scored_candidate(candidate, career_title="Programmer"):
    """Build a minimal published solution + 1 assessment + 1 variable +
    1 exact-match band configuration. Returns (solution, candidate)."""
    solution = ProfilingSolution.objects.create(
        title="S",
        status="published",
        created_by=candidate,
    )
    a = Assessment.objects.create(title="A", status="published")
    sa = SelectedAssessment.objects.create(solution=solution, assessment=a, label="A1")
    s = AssessmentSection.objects.create(assessment=a, title="V1", level=1, order=1)
    bd = BandDefinition.objects.create(selected_assessment=sa, section=s)
    # 5-band config: 1=L(0-20), 2=BL(20-40), 3=AVG(40-60), 4=AH(60-80), 5=H(80-100)
    for n, lo, hi, code in [
        (1, 0, 20, "L"),
        (2, 20, 40, "BL"),
        (3, 40, 60, "AVG"),
        (4, 60, 80, "AH"),
        (5, 80, 100, "H"),
    ]:
        Band.objects.create(
            band_definition=bd, band_number=n, range_min=lo, range_max=hi, band_code=code
        )

    session = AssessmentSession.objects.create(
        assessment=a, candidate=candidate, status="completed"
    )
    SectionScore.objects.create(
        session=session, section=s, raw_score=90.0, max_score=100.0
    )  # 90% → band 5

    MappingCriterion.objects.create(
        solution=solution,
        career_title=career_title,
        section=s,
        criterion_band_code="H",  # band 5 → exact match
        weight=1.0,
    )
    return solution


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_compute_endpoint_returns_match_index(psy_client, psychometrician_user):
    """POST /solutions/<id>/compute/ creates a MatchIndex and returns it."""
    solution = _make_solution_with_scored_candidate(psychometrician_user)
    resp = psy_client.post(
        f"/api/career-profiling/solutions/{solution.id}/compute/", {}, format="json"
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    data = resp.data["data"]
    assert len(data) == 1
    assert data[0]["career_title"] == "Programmer"
    assert data[0]["final_match_index"] is not None
    assert data[0]["variable_mapping_index"] == 100.0
    # MatchIndex persisted
    assert MatchIndex.objects.filter(solution=solution).count() == 1


def test_compute_endpoint_rejects_draft_solution(psy_client, psychometrician_user):
    """Solutions in 'draft' status can't be computed — must be published."""
    solution = _make_solution_with_scored_candidate(psychometrician_user)
    solution.status = "draft"
    solution.save(update_fields=["status"])
    resp = psy_client.post(
        f"/api/career-profiling/solutions/{solution.id}/compute/", {}, format="json"
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "forbidden"


def test_admin_can_compute_for_other_candidate(psy_client, psychometrician_user, individual_user):
    """Psychometrician may pass candidate_id in the body to compute for any user."""
    # Build solution owned by psychometrician, candidate is the individual user
    solution = _make_solution_with_scored_candidate(individual_user)
    resp = psy_client.post(
        f"/api/career-profiling/solutions/{solution.id}/compute/",
        {"candidate_id": individual_user.id},
        format="json",
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    assert len(resp.data["data"]) == 1
    mi = MatchIndex.objects.first()
    assert mi.candidate_id == individual_user.id


def test_non_admin_computes_for_self(individual_client, individual_user):
    """Individual user calling compute (without candidate_id) computes for self."""
    solution = _make_solution_with_scored_candidate(individual_user)
    resp = individual_client.post(
        f"/api/career-profiling/solutions/{solution.id}/compute/", {}, format="json"
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.data}"
    mi = MatchIndex.objects.first()
    assert mi.candidate_id == individual_user.id


def test_non_admin_candidate_id_is_ignored(
    individual_client, individual_user, psychometrician_user
):
    """When a non-admin passes candidate_id, it's ignored — they only compute
    for themselves. This prevents privilege escalation."""
    solution = _make_solution_with_scored_candidate(individual_user)
    # Individual user tries to compute for psychometrician
    resp = individual_client.post(
        f"/api/career-profiling/solutions/{solution.id}/compute/",
        {"candidate_id": psychometrician_user.id},
        format="json",
    )
    assert resp.status_code == 200
    # But the MatchIndex is for the individual user, not the psychometrician
    mi = MatchIndex.objects.first()
    assert mi.candidate_id == individual_user.id
    assert mi.candidate_id != psychometrician_user.id


def test_compute_is_idempotent(psy_client, psychometrician_user):
    """Two calls to /compute/ produce one MatchIndex row, not two."""
    solution = _make_solution_with_scored_candidate(psychometrician_user)
    psy_client.post(f"/api/career-profiling/solutions/{solution.id}/compute/", {}, format="json")
    psy_client.post(f"/api/career-profiling/solutions/{solution.id}/compute/", {}, format="json")
    assert MatchIndex.objects.filter(solution=solution).count() == 1
