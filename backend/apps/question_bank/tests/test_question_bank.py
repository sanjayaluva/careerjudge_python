"""Tests for the question_bank module."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory

User = get_user_model()


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def psychometrician_role(roles):
    return roles["psychometrician"]


@pytest.fixture
def sme_role(roles):
    return roles["sme"]


@pytest.fixture
def reviewer_role(roles):
    return roles["reviewer"]


@pytest.fixture
def individual_role(roles):
    return roles["individual"]


@pytest.fixture
def psychometrician_user(db, psychometrician_role):
    for action in ("view", "add", "change", "delete", "review"):
        ModuleRight.objects.get_or_create(
            role=psychometrician_role, module="question_bank", action=action
        )
    return UserFactory(role=psychometrician_role, email="psy@test.com")


@pytest.fixture
def sme_user(db, sme_role):
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=sme_role, module="question_bank", action=action)
    return UserFactory(role=sme_role, email="sme@test.com")


@pytest.fixture
def reviewer_user(db, reviewer_role):
    for action in ("view", "review", "approve", "reject"):
        ModuleRight.objects.get_or_create(role=reviewer_role, module="question_bank", action=action)
    return UserFactory(role=reviewer_role, email="reviewer@test.com")


@pytest.fixture
def individual_user(db, individual_role):
    return UserFactory(role=individual_role, email="ind@test.com")


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def psy_client(db, psychometrician_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(psychometrician_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def sme_client(db, sme_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(sme_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def reviewer_client(db, reviewer_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(reviewer_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def individual_client(db, individual_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(individual_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# Category Tests (UC010, UC011, UC012)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCategoryCRUD:
    def test_psy_can_list_categories(self, psy_client):
        resp = psy_client.get("/api/question-bank/categories/")
        assert resp.status_code == 200

    def test_psy_can_create_category(self, psy_client):
        resp = psy_client.post(
            "/api/question-bank/categories/",
            {"name": "Aptitude", "description": "Aptitude questions"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Aptitude"

    def test_create_subcategory(self, psy_client):
        parent_resp = psy_client.post(
            "/api/question-bank/categories/",
            {"name": "Aptitude"},
            format="json",
        )
        parent_id = parent_resp.json()["data"]["id"]
        resp = psy_client.post(
            "/api/question-bank/categories/",
            {"name": "Numerical", "parent": parent_id},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["parent"] == parent_id

    def test_category_full_path(self, psy_client):
        parent_resp = psy_client.post(
            "/api/question-bank/categories/", {"name": "Aptitude"}, format="json"
        )
        parent_id = parent_resp.json()["data"]["id"]
        child_resp = psy_client.post(
            "/api/question-bank/categories/",
            {"name": "Numerical", "parent": parent_id},
            format="json",
        )
        child_id = child_resp.json()["data"]["id"]
        detail_resp = psy_client.get(f"/api/question-bank/categories/{child_id}/")
        assert "Aptitude > Numerical" in detail_resp.json()["data"]["full_path"]

    def test_category_tree(self, psy_client):
        parent_resp = psy_client.post(
            "/api/question-bank/categories/", {"name": "Root"}, format="json"
        )
        parent_id = parent_resp.json()["data"]["id"]
        psy_client.post(
            "/api/question-bank/categories/",
            {"name": "Child1", "parent": parent_id},
            format="json",
        )
        resp = psy_client.get("/api/question-bank/categories/tree/")
        assert resp.status_code == 200

    def test_individual_cannot_create_category(self, individual_client):
        resp = individual_client.post(
            "/api/question-bank/categories/",
            {"name": "Test"},
            format="json",
        )
        assert resp.status_code == 403

    def test_psy_can_delete_category(self, psy_client):
        create_resp = psy_client.post(
            "/api/question-bank/categories/", {"name": "ToDelete"}, format="json"
        )
        cat_id = create_resp.json()["data"]["id"]
        resp = psy_client.delete(f"/api/question-bank/categories/{cat_id}/")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Question Tests (UC013, UC016, UC017)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQuestionCRUD:
    def test_sme_can_create_question(self, sme_client):
        resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Math Question",
                "question_text_1": "What is 2 + 2?",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "draft"
        assert resp.json()["data"]["created_by"] is not None

    def test_sme_can_create_all_question_types(self, sme_client):
        """Test creating questions of different types."""
        types = [
            "MCQ_TEXT_IMAGE",
            "FITB_SINGLE",
            "MATCH_FOLLOWING",
            "HOTSPOT_SINGLE",
            "RANK_SIMPLE",
            "STANDARD_RATING_SCALE",
            "FORCED_CHOICE_SINGLE_LEVEL",
        ]
        for qtype in types:
            resp = sme_client.post(
                "/api/question-bank/questions/",
                {
                    "question_type": qtype,
                    "question_title": f"Test {qtype}",
                    "question_text_1": f"Question of type {qtype}",
                    "scoring_type": "BINARY",
                },
                format="json",
            )
            assert resp.status_code == 201, f"Failed for type {qtype}: {resp.content}"

    def test_sme_can_list_questions(self, sme_client):
        sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Test Q Title",
                "question_text_1": "Test Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        resp = sme_client.get("/api/question-bank/questions/")
        assert resp.status_code == 200

    def test_sme_can_retrieve_question(self, sme_client):
        create_resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Detail Q Title",
                "question_text_1": "Detail Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        qid = create_resp.json()["data"]["id"]
        resp = sme_client.get(f"/api/question-bank/questions/{qid}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["question_text_1"] == "Detail Q"

    def test_sme_can_edit_draft_question(self, sme_client):
        create_resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Original Title",
                "question_text_1": "Original",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        qid = create_resp.json()["data"]["id"]
        resp = sme_client.patch(
            f"/api/question-bank/questions/{qid}/",
            {"question_text_1": "Updated text"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["question_text_1"] == "Updated text"

    def test_cannot_edit_submitted_question(self, sme_client):
        create_resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Q Title",
                "question_text_1": "Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        qid = create_resp.json()["data"]["id"]
        # Add options so submit_for_review validation passes
        from apps.question_bank.models import Question as QModel
        from apps.question_bank.models import ResponseOption

        q = QModel.objects.get(id=qid)
        ResponseOption.objects.create(
            question=q, option_type="TEXT", text_value="A", is_correct=True, order=1
        )
        ResponseOption.objects.create(
            question=q, option_type="TEXT", text_value="B", is_correct=False, order=2
        )
        # Submit for review
        sme_client.post(f"/api/question-bank/questions/{qid}/submit_for_review/")
        # Try to edit
        resp = sme_client.patch(
            f"/api/question-bank/questions/{qid}/",
            {"question_title": "Changed Title", "question_text_1": "Changed"},
            format="json",
        )
        assert resp.status_code == 403

    def test_sme_can_delete_draft_question(self, sme_client):
        create_resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Delete Me Title",
                "question_text_1": "Delete me",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        qid = create_resp.json()["data"]["id"]
        resp = sme_client.delete(f"/api/question-bank/questions/{qid}/")
        assert resp.status_code == 200

    def test_individual_cannot_create_question(self, individual_client):
        resp = individual_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Test Title",
                "question_text_1": "Test",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        assert resp.status_code == 403

    def test_filter_questions_by_type(self, sme_client):
        sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "MCQ Q Title",
                "question_text_1": "MCQ Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "FITB_SINGLE",
                "question_title": "FITB Q Title",
                "question_text_1": "FITB Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        resp = sme_client.get("/api/question-bank/questions/?question_type=FITB_SINGLE")
        assert resp.status_code == 200

    def test_filter_questions_mine(self, sme_client):
        sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "My Q Title",
                "question_text_1": "My Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        resp = sme_client.get("/api/question-bank/questions/?mine=true")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Review Workflow Tests (UC014, UC015)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReviewWorkflow:
    def _create_and_submit(self, sme_client):
        """Helper: create a question and submit for review."""
        create_resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Review Q Title",
                "question_text_1": "Review Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        qid = create_resp.json()["data"]["id"]
        # Add options so the question passes validation
        from apps.question_bank.models import Question, ResponseOption

        q = Question.objects.get(id=qid)
        ResponseOption.objects.create(
            question=q, option_type="TEXT", text_value="A", is_correct=True, order=1
        )
        ResponseOption.objects.create(
            question=q, option_type="TEXT", text_value="B", is_correct=False, order=2
        )
        sme_client.post(f"/api/question-bank/questions/{qid}/submit_for_review/")
        return qid

    def test_sme_submit_for_review(self, sme_client):
        create_resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Q Title",
                "question_text_1": "Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        qid = create_resp.json()["data"]["id"]
        # Add options so validation passes
        from apps.question_bank.models import Question as QModel
        from apps.question_bank.models import ResponseOption

        q = QModel.objects.get(id=qid)
        ResponseOption.objects.create(
            question=q, option_type="TEXT", text_value="A", is_correct=True, order=1
        )
        ResponseOption.objects.create(
            question=q, option_type="TEXT", text_value="B", is_correct=False, order=2
        )
        resp = sme_client.post(f"/api/question-bank/questions/{qid}/submit_for_review/")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "pending_content_review"

    def test_cannot_submit_non_draft(self, sme_client):
        create_resp = sme_client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "MCQ_TEXT_IMAGE",
                "question_title": "Q Title",
                "question_text_1": "Q",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        qid = create_resp.json()["data"]["id"]
        # Add options so the first submission succeeds
        from apps.question_bank.models import Question as QModel
        from apps.question_bank.models import ResponseOption

        q = QModel.objects.get(id=qid)
        ResponseOption.objects.create(
            question=q, option_type="TEXT", text_value="A", is_correct=True, order=1
        )
        ResponseOption.objects.create(
            question=q, option_type="TEXT", text_value="B", is_correct=False, order=2
        )
        sme_client.post(f"/api/question-bank/questions/{qid}/submit_for_review/")
        # Try to submit again — should fail with 403 (already pending)
        resp = sme_client.post(f"/api/question-bank/questions/{qid}/submit_for_review/")
        assert resp.status_code == 403

    def test_reviewer_can_approve_content(self, sme_client, reviewer_client):
        qid = self._create_and_submit(sme_client)
        resp = reviewer_client.post(
            f"/api/question-bank/questions/{qid}/review/",
            {
                "review_type": "content",
                "action": "approve",
                "comment": "Looks good",
                "rating": 4,
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["question_status"] == "pending_psychometric_review"

    def test_reviewer_can_send_back(self, sme_client, reviewer_client):
        qid = self._create_and_submit(sme_client)
        resp = reviewer_client.post(
            f"/api/question-bank/questions/{qid}/review/",
            {
                "review_type": "content",
                "action": "send_back",
                "comment": "Fix the grammar",
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["question_status"] == "sent_back"

    def test_reviewer_can_reject(self, sme_client, reviewer_client):
        qid = self._create_and_submit(sme_client)
        resp = reviewer_client.post(
            f"/api/question-bank/questions/{qid}/review/",
            {
                "review_type": "content",
                "action": "reject",
                "comment": "Not suitable",
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["question_status"] == "rejected"

    def test_full_workflow_approve(self, sme_client, reviewer_client, psy_client):
        """Full workflow: SME → Reviewer approve → Psychometrician approve → confirmed."""
        # Create + submit
        qid = self._create_and_submit(sme_client)

        # Reviewer approves
        resp = reviewer_client.post(
            f"/api/question-bank/questions/{qid}/review/",
            {"review_type": "content", "action": "approve", "comment": "OK", "rating": 5},
            format="json",
        )
        assert resp.status_code == 200

        # Psychometrician approves
        resp = psy_client.post(
            f"/api/question-bank/questions/{qid}/review/",
            {
                "review_type": "psychometric",
                "action": "approve",
                "comment": "Psychometrically sound",
                "rating": 4,
                "exposure_limit": 100,
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["question_status"] == "confirmed"

    def test_review_history(self, sme_client, reviewer_client):
        qid = self._create_and_submit(sme_client)
        reviewer_client.post(
            f"/api/question-bank/questions/{qid}/review/",
            {"review_type": "content", "action": "approve", "comment": "Good", "rating": 5},
            format="json",
        )
        resp = sme_client.get(f"/api/question-bank/questions/{qid}/reviews/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["action"] == "approve"

    def test_individual_cannot_review(self, sme_client, individual_client):
        qid = self._create_and_submit(sme_client)
        resp = individual_client.post(
            f"/api/question-bank/questions/{qid}/review/",
            {"review_type": "content", "action": "approve"},
            format="json",
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQuestionModel:
    def test_can_be_edited_draft(self):
        from apps.question_bank.models import Question

        q = Question(
            question_type="MCQ_TEXT_IMAGE",
            question_title="Test Title",
            question_text_1="Test",
            status="draft",
        )
        assert q.can_be_edited is True

    def test_can_be_edited_sent_back(self):
        from apps.question_bank.models import Question

        q = Question(
            question_type="MCQ_TEXT_IMAGE",
            question_title="Test Title",
            question_text_1="Test",
            status="sent_back",
        )
        assert q.can_be_edited is True

    def test_cannot_be_edited_pending_review(self):
        from apps.question_bank.models import Question

        q = Question(
            question_type="MCQ_TEXT_IMAGE",
            question_title="Test Title",
            question_text_1="Test",
            status="pending_content_review",
        )
        assert q.can_be_edited is False

    def test_is_in_question_bank_confirmed(self):
        from apps.question_bank.models import Question

        q = Question(
            question_type="MCQ_TEXT_IMAGE",
            question_title="Test Title",
            question_text_1="Test",
            status="confirmed",
            is_active=True,
        )
        assert q.is_in_question_bank is True

    def test_is_not_in_question_bank_draft(self):
        from apps.question_bank.models import Question

        q = Question(
            question_type="MCQ_TEXT_IMAGE",
            question_title="Test Title",
            question_text_1="Test",
            status="draft",
        )
        assert q.is_in_question_bank is False

    # --- is_psychometric / question_category property tests ---

    def test_mcq_is_not_psychometric(self):
        from apps.question_bank.models import Question

        q = Question(
            question_type="MCQ_TEXT_IMAGE",
            question_title="Test Title",
            question_text_1="Test",
            status="draft",
        )
        assert q.is_psychometric is False
        assert q.question_category == "normal"

    @pytest.mark.parametrize(
        "qtype",
        [
            "MCQ_TEXT_IMAGE",
            "MCQ_TEXT_IMAGE_IMG_OPTIONS",
            "MCQ_AUDIO_MULTI",
            "MCQ_VIDEO_MULTI",
            "MCQ_WORD_FLASH_MULTI",
            "MCQ_IMAGE_FLASH_MULTI",
            "MCQ_PASSAGE_DISPLAY_MULTI",
            "MCQ_IMAGE_DISPLAY_MULTI",
            "FITB_SINGLE",
            "FITB_MULTI_FIELD",
            "FITB_WORD_FLASH_MULTI",
            "FITB_IMAGE_FLASH_MULTI",
            "MATCH_FOLLOWING",
            "GRID_LIST_SELECTION",
            "HOTSPOT_SINGLE",
            "HOTSPOT_MULTI",
        ],
    )
    def test_normal_question_types_are_not_psychometric(self, qtype):
        from apps.question_bank.models import Question

        q = Question(
            question_type=qtype,
            question_title="Test Title",
            question_text_1="Test",
            status="draft",
        )
        assert q.is_psychometric is False
        assert q.question_category == "normal"

    @pytest.mark.parametrize(
        "qtype",
        [
            "RANK_SIMPLE",
            "RANK_THEN_RATE",
            "STANDARD_RATING_SCALE",
            "FORCED_CHOICE_SINGLE_LEVEL",
            "FORCED_CHOICE_TWO_LEVEL",
        ],
    )
    def test_psychometric_question_types_are_psychometric(self, qtype):
        from apps.question_bank.models import Question

        q = Question(
            question_type=qtype,
            question_title="Test Title",
            question_text_1="Test",
            status="draft",
        )
        assert q.is_psychometric is True
        assert q.question_category == "psychometric"


@pytest.mark.django_db
class TestHotspotAreaModel:
    def test_contains_point_inside(self):
        from apps.question_bank.models import HotspotArea

        area = HotspotArea(x=100, y=100, width_px=50, height_px=50)
        assert area.contains_point(120, 120) is True

    def test_contains_point_outside(self):
        from apps.question_bank.models import HotspotArea

        area = HotspotArea(x=100, y=100, width_px=50, height_px=50)
        assert area.contains_point(200, 200) is False

    def test_contains_point_edge(self):
        from apps.question_bank.models import HotspotArea

        area = HotspotArea(x=100, y=100, width_px=50, height_px=50)
        assert area.contains_point(150, 150) is True  # bottom-right corner


@pytest.mark.django_db
class TestCategoryModel:
    def test_full_path_root(self, psy_client):
        from apps.question_bank.models import Category

        cat = Category.objects.create(name="Root")
        assert cat.full_path == "Root"

    def test_full_path_nested(self, psy_client):
        from apps.question_bank.models import Category

        parent = Category.objects.create(name="Parent")
        child = Category.objects.create(name="Child", parent=parent)
        assert child.full_path == "Parent > Child"
