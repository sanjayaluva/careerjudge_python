"""Tests for the D1/D2 dossier "medium" gap items implemented for
question_bank:

  1. worked_solution field (D1)
  2. Periodic QB updation: expires_at + batch activate/inactivate +
     batch exposure-limit management (D1)
  3. Manual psychometric-analysis path: download response data / upload
     computed values (D2)
  4. Psychometric analysis filters: region / age range / category (D2)
"""

import csv
import io

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, UserProfile
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import Assessment, AssessmentSession, QuestionAttempt
from apps.question_bank.models import Category, Question
from apps.question_bank.psychometrics import (
    extract_response_rows,
    run_psychometric_analysis,
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
    for action in ("view", "add", "change", "delete", "review"):
        ModuleRight.objects.get_or_create(role=role, module="question_bank", action=action)
    return UserFactory(role=role, email="psy-dossier@test.com")


@pytest.fixture
def sme_user(db, roles):
    role = roles["sme"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="question_bank", action=action)
    return UserFactory(role=role, email="sme-dossier@test.com")


def _client_for(user):
    c = APIClient()
    refresh = RefreshToken.for_user(user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def psy_client(db, psychometrician_user):
    return _client_for(psychometrician_user)


@pytest.fixture
def sme_client(db, sme_user):
    return _client_for(sme_user)


def _make_question(category=None, **kwargs):
    category = category or Category.objects.create(name=f"Cat-{Question.objects.count()}")
    defaults = {
        "category": category,
        "question_type": "MCQ_TEXT_IMAGE",
        "question_title": "T",
        "question_text_1": "Q?",
        "scoring_type": "BINARY",
        "status": "confirmed",
    }
    defaults.update(kwargs)
    return Question.objects.create(**defaults)


def _make_candidate(email, **profile_kwargs):
    from apps.assessment.tests.factories import get_or_create_role

    user = UserFactory.create(role=get_or_create_role("individual", is_system=True), email=email)
    if profile_kwargs:
        UserProfile.objects.create(user=user, **profile_kwargs)
    return user


def _make_completed_session(assessment, candidate, total_score):
    return AssessmentSession.objects.create(
        assessment=assessment,
        candidate=candidate,
        status="completed",
        total_score=float(total_score),
        max_score=10.0,
        percentage=(float(total_score) / 10.0) * 100,
    )


def _make_attempt(session, question, score, max_score=1.0):
    return QuestionAttempt.objects.create(
        session=session,
        question=question,
        status="attempted",
        score=float(score),
        max_score=float(max_score),
    )


# ---------------------------------------------------------------------------
# 1. worked_solution field
# ---------------------------------------------------------------------------


class TestWorkedSolutionField:
    def test_create_and_retrieve_worked_solution(self, sme_client):
        resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "T",
                "question_text_1": "2+2=?",
                "worked_solution": "Add 2 and 2 to get 4.",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        data = resp.json()["data"]
        assert data["worked_solution"] == "Add 2 and 2 to get 4."

        qid = data["id"]
        get_resp = sme_client.get(f"/api/question-bank/questions/{qid}/")
        assert get_resp.json()["data"]["worked_solution"] == "Add 2 and 2 to get 4."

    def test_update_worked_solution(self, sme_client, sme_user):
        q = _make_question(status="draft", created_by=sme_user)
        resp = sme_client.patch(
            f"/api/question-bank/questions/{q.id}/",
            {"worked_solution": "Updated solution text."},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        q.refresh_from_db()
        assert q.worked_solution == "Updated solution text."

    def test_worked_solution_defaults_blank(self, sme_client):
        resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "T2",
                "question_text_1": "Q?",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        assert resp.json()["data"]["worked_solution"] == ""


# ---------------------------------------------------------------------------
# 2. Periodic QB updation: expires_at filter + batch actions
# ---------------------------------------------------------------------------


class TestPeriodicQBUpdation:
    def test_expired_filter(self, psy_client):
        from django.utils import timezone

        past = _make_question(expires_at=timezone.now() - timezone.timedelta(days=1))
        future = _make_question(expires_at=timezone.now() + timezone.timedelta(days=30))
        never = _make_question()  # expires_at is null

        resp = psy_client.get("/api/question-bank/questions/?expired=true")
        ids = {row["id"] for row in resp.json()["data"]["results"]}
        assert ids == {past.id}

        resp = psy_client.get("/api/question-bank/questions/?expired=false")
        ids = {row["id"] for row in resp.json()["data"]["results"]}
        assert ids == {future.id, never.id}

    def test_batch_status_activate_inactivate(self, psy_client):
        q1 = _make_question(is_active=True)
        q2 = _make_question(is_active=True)

        resp = psy_client.post(
            "/api/question-bank/questions/batch-status/",
            {"question_ids": [q1.id, q2.id, 999999], "is_active": False},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()["data"]
        assert sorted(data["updated_ids"]) == sorted([q1.id, q2.id])
        assert data["missing_ids"] == [999999]
        q1.refresh_from_db()
        q2.refresh_from_db()
        assert q1.is_active is False
        assert q2.is_active is False

        # Re-activate (Activation of Expired Questions)
        resp = psy_client.post(
            "/api/question-bank/questions/batch-status/",
            {"question_ids": [q1.id], "is_active": True},
            format="json",
        )
        assert resp.status_code == 200
        q1.refresh_from_db()
        assert q1.is_active is True

    def test_batch_status_requires_question_ids_and_is_active(self, psy_client):
        resp = psy_client.post(
            "/api/question-bank/questions/batch-status/", {"is_active": True}, format="json"
        )
        assert resp.status_code == 400

        q1 = _make_question()
        resp = psy_client.post(
            "/api/question-bank/questions/batch-status/",
            {"question_ids": [q1.id]},
            format="json",
        )
        assert resp.status_code == 400

    def test_batch_exposure_limit_set_and_clear(self, psy_client):
        q1 = _make_question()
        q2 = _make_question()

        resp = psy_client.post(
            "/api/question-bank/questions/batch-exposure-limit/",
            {"question_ids": [q1.id, q2.id], "exposure_limit": 250},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        q1.refresh_from_db()
        q2.refresh_from_db()
        assert q1.exposure_limit == 250
        assert q2.exposure_limit == 250

        # Clear (unlimited exposure)
        resp = psy_client.post(
            "/api/question-bank/questions/batch-exposure-limit/",
            {"question_ids": [q1.id], "exposure_limit": None},
            format="json",
        )
        assert resp.status_code == 200
        q1.refresh_from_db()
        assert q1.exposure_limit is None

    def test_batch_exposure_limit_rejects_invalid_value(self, psy_client):
        q1 = _make_question()
        resp = psy_client.post(
            "/api/question-bank/questions/batch-exposure-limit/",
            {"question_ids": [q1.id], "exposure_limit": 0},
            format="json",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 3 + 4. Manual psychometric-analysis path + region/age/category filters
# ---------------------------------------------------------------------------


class TestManualPsychometricPath:
    def test_download_response_data_csv(self, psy_client):
        q = _make_question()
        assessment = Assessment.objects.create(title="A", status="published")
        for i in range(3):
            c = _make_candidate(f"cand{i}@test.com")
            s = _make_completed_session(assessment, c, total_score=5 + i)
            _make_attempt(s, q, score=1.0 if i % 2 == 0 else 0.0)

        resp = psy_client.post(
            "/api/question-bank/questions/psychometric-data-download/",
            {"question_ids": [q.id]},
            format="json",
        )
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(resp.content.decode("utf-8"))))
        assert len(rows) == 3
        assert {row["question_id"] for row in rows} == {str(q.id)}

    def test_upload_manual_values_persists_on_question(self, psy_client):
        q = _make_question()
        resp = psy_client.post(
            "/api/question-bank/questions/psychometric-upload/",
            {
                "results": [
                    {
                        "question_id": q.id,
                        "item_difficulty_index": 0.55,
                        "discrimination_index": 0.31,
                    }
                ]
            },
            format="json",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()["data"]
        assert data["updated_ids"] == [q.id]
        assert data["errors"] == []
        q.refresh_from_db()
        assert q.item_difficulty_index == 0.55
        assert q.discrimination_index == 0.31
        assert q.psychometric_analyzed_at is not None

    def test_upload_reports_errors_for_missing_question_and_empty_fields(self, psy_client):
        q = _make_question()
        resp = psy_client.post(
            "/api/question-bank/questions/psychometric-upload/",
            {
                "results": [
                    {"question_id": 999999, "item_difficulty_index": 0.5},
                    {"question_id": q.id},  # no index fields
                ]
            },
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["updated_ids"] == []
        assert len(data["errors"]) == 2

    def test_category_filter_auto_extracts_questions(self, psy_client):
        cat = Category.objects.create(name="Auto-extract cat")
        q1 = _make_question(category=cat)
        q2 = _make_question(category=cat)
        _make_question()  # different category — should not be included

        resp = psy_client.post(
            "/api/question-bank/questions/psychometric_analysis/",
            {"category_id": cat.id},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        result_ids = {row["question_id"] for row in resp.json()["data"]}
        assert result_ids == {q1.id, q2.id}

    def test_region_filter_restricts_candidates(self):
        q = _make_question()
        assessment = Assessment.objects.create(title="A", status="published")
        c_in = _make_candidate("region-in@test.com", state_province="Karnataka")
        c_out = _make_candidate("region-out@test.com", state_province="Kerala")
        for c in (c_in, c_out):
            s = _make_completed_session(assessment, c, total_score=5)
            _make_attempt(s, q, score=1.0)

        result = run_psychometric_analysis(q, region="Karnataka")
        assert result.n_candidates == 1

        result_all = run_psychometric_analysis(q)
        assert result_all.n_candidates == 2

    def test_age_range_filter_restricts_candidates(self):
        import datetime

        q = _make_question()
        assessment = Assessment.objects.create(title="A", status="published")
        young = _make_candidate(
            "young@test.com",
            date_of_birth=datetime.date.today() - datetime.timedelta(days=20 * 365),
        )
        old = _make_candidate(
            "old@test.com", date_of_birth=datetime.date.today() - datetime.timedelta(days=50 * 365)
        )
        for c in (young, old):
            s = _make_completed_session(assessment, c, total_score=5)
            _make_attempt(s, q, score=1.0)

        result = run_psychometric_analysis(q, age_min=18, age_max=25)
        assert result.n_candidates == 1

        result_all = run_psychometric_analysis(q)
        assert result_all.n_candidates == 2

    def test_extract_response_rows_helper(self):
        q = _make_question()
        assessment = Assessment.objects.create(title="A", status="published")
        c = _make_candidate("extract@test.com")
        s = _make_completed_session(assessment, c, total_score=7)
        _make_attempt(s, q, score=1.0, max_score=1.0)

        rows = extract_response_rows(q)
        assert len(rows) == 1
        row = rows[0]
        assert row["question_id"] == q.id
        assert row["target_score"] == 1.0
        assert row["total_score"] == 7.0
        assert row["is_correct"] is True
