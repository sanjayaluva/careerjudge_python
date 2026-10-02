"""Report 9 #77: the candidate's profiling solutions split into Not attempted /
Suspended / Completed, from his sessions on each solution's selected
assessments."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import Assessment, AssessmentSession
from apps.career_profiling.models import ProfilingSolution, SelectedAssessment

pytestmark = pytest.mark.django_db


@pytest.fixture
def candidate(db):
    role = get_or_create_default_roles()["individual"]
    ModuleRight.objects.get_or_create(role=role, module="career_profiling", action="view")
    return UserFactory(role=role, email="cand@test.com")


def _solution(title, *assessments):
    sol = ProfilingSolution.objects.create(title=title, status="published")
    for i, a in enumerate(assessments):
        SelectedAssessment.objects.create(solution=sol, assessment=a, label=f"A{i}", order=i)
    return sol


def _rows(user):
    c = APIClient()
    c.force_authenticate(user=user)
    resp = c.get("/api/career-profiling/solutions/")
    assert resp.status_code == 200
    return {r["title"]: r for r in resp.data["data"]["results"]}


def test_candidate_status_per_solution(candidate):
    a1 = Assessment.objects.create(title="Aptitude", status="published")
    a2 = Assessment.objects.create(title="Interest", status="published")
    a3 = Assessment.objects.create(title="Values", status="published")
    a4 = Assessment.objects.create(title="Polar", status="published")
    a5 = Assessment.objects.create(title="Skills", status="published")
    _solution("Untouched", a1, a5)
    _solution("Half done", a2, a3)
    _solution("Done", a3, a4)
    # a2 suspended; a3 and a4 completed; a1 and a5 never started.
    AssessmentSession.objects.create(assessment=a2, candidate=candidate, status="suspended")
    AssessmentSession.objects.create(assessment=a3, candidate=candidate, status="completed")
    AssessmentSession.objects.create(assessment=a4, candidate=candidate, status="completed")

    rows = _rows(candidate)
    assert rows["Untouched"]["my_status"] == "not_attempted"
    assert rows["Half done"]["my_status"] == "suspended"
    assert rows["Done"]["my_status"] == "completed"
    assert [(a["title"], a["status"]) for a in rows["Half done"]["my_assessments"]] == [
        ("Interest", "in_progress"),
        ("Values", "completed"),
    ]


def test_status_is_the_requesting_candidates_own(candidate):
    a1 = Assessment.objects.create(title="Aptitude", status="published")
    _solution("Solo", a1)
    other = UserFactory(role=candidate.role, email="other@test.com")
    AssessmentSession.objects.create(assessment=a1, candidate=other, status="completed")
    assert _rows(candidate)["Solo"]["my_status"] == "not_attempted"
    assert _rows(other)["Solo"]["my_status"] == "completed"


def test_solution_with_no_assessments_is_not_attempted(candidate):
    ProfilingSolution.objects.create(title="Empty", status="published")
    assert _rows(candidate)["Empty"]["my_status"] == "not_attempted"
