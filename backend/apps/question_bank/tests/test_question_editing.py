"""Tests for question editing workflow.

Business rules:
  1. cj_admin can edit ANY question regardless of status (override).
  2. SME and custom roles with 'change' permission can only edit questions
     in 'draft' or 'sent_back' status.
  3. Once a question is submitted for review or confirmed/added to the
     question bank, it is locked for non-admin users.
  4. Custom roles with question_bank 'change' permission can also edit
     (same rules as SME — draft or sent_back only).
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.question_bank.models import Question


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def sme_user(db, roles):
    sme_role = roles["sme"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=sme_role, module="question_bank", action=action)
    return UserFactory(role=sme_role, email="sme-edit@test.com")


@pytest.fixture
def cj_admin_user(db, roles):
    admin_role = roles["cj_admin"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=admin_role, module="question_bank", action=action)
    return UserFactory(role=admin_role, email="admin-edit@test.com")


@pytest.fixture
def custom_role_user(db, roles):
    """A custom role based on sme with question_bank change permission."""
    sme_role = roles["sme"]
    custom = Role.objects.create(
        name="custom_question_editor",
        description="Custom role for testing",
        is_system=False,
        base_role=sme_role,
    )
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.create(role=custom, module="question_bank", action=action)
    return UserFactory(role=custom, email="custom-edit@test.com")


@pytest.fixture
def sme_client(db, sme_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(sme_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def admin_client(db, cj_admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(cj_admin_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def custom_client(db, custom_role_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(custom_role_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# Tests: SME editing rules
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sme_can_edit_draft_question(sme_client, sme_user):
    """SME can edit a question in 'draft' status."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Original Question",
        question_text_1="Original question",
        scoring_type="BINARY",
        status="draft",
        created_by=sme_user,
    )
    resp = sme_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Edited question text"},
        format="json",
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    q.refresh_from_db()
    assert q.question_text_1 == "Edited question text"


@pytest.mark.django_db
def test_sme_can_edit_sent_back_question(sme_client, sme_user):
    """SME can edit a question that was sent back by a reviewer."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Sent Back Question",
        question_text_1="Sent back question",
        scoring_type="BINARY",
        status="sent_back",
        created_by=sme_user,
    )
    resp = sme_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Revised after send-back"},
        format="json",
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    q.refresh_from_db()
    assert q.question_text_1 == "Revised after send-back"


@pytest.mark.django_db
def test_sme_cannot_edit_pending_review_question(sme_client, sme_user):
    """SME cannot edit a question that's pending content review."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Pending Review",
        question_text_1="Pending review",
        scoring_type="BINARY",
        status="pending_content_review",
        created_by=sme_user,
    )
    resp = sme_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Trying to edit"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "forbidden"


@pytest.mark.django_db
def test_sme_cannot_edit_confirmed_question(sme_client, sme_user):
    """SME cannot edit a confirmed question (already in question bank)."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Confirmed Question",
        question_text_1="Confirmed question",
        scoring_type="BINARY",
        status="confirmed",
        created_by=sme_user,
    )
    resp = sme_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Trying to edit confirmed"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "forbidden"


# ---------------------------------------------------------------------------
# Tests: CJ Admin override
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cj_admin_can_edit_draft_question(admin_client, sme_user):
    """CJ Admin can edit a draft question (same as SME)."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Draft Title",
        question_text_1="Draft",
        scoring_type="BINARY",
        status="draft",
        created_by=sme_user,
    )
    resp = admin_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Admin edited draft"},
        format="json",
    )
    assert resp.status_code == 200
    q.refresh_from_db()
    assert q.question_text_1 == "Admin edited draft"


@pytest.mark.django_db
def test_cj_admin_can_edit_confirmed_question(admin_client, sme_user):
    """CJ Admin can edit a confirmed question (override status check)."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Confirmed Title",
        question_text_1="Confirmed by psychometrician",
        scoring_type="BINARY",
        status="confirmed",
        created_by=sme_user,
    )
    resp = admin_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Admin override edit on confirmed question"},
        format="json",
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    q.refresh_from_db()
    assert q.question_text_1 == "Admin override edit on confirmed question"


@pytest.mark.django_db
def test_cj_admin_can_edit_pending_review_question(admin_client, sme_user):
    """CJ Admin can edit a question pending review (override)."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Pending Title",
        question_text_1="Pending",
        scoring_type="BINARY",
        status="pending_content_review",
        created_by=sme_user,
    )
    resp = admin_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Admin override edit on pending question"},
        format="json",
    )
    assert resp.status_code == 200
    q.refresh_from_db()
    assert q.question_text_1 == "Admin override edit on pending question"


@pytest.mark.django_db
def test_cj_admin_can_delete_confirmed_question(admin_client, sme_user):
    """CJ Admin can delete a confirmed question (override)."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Confirmed Title",
        question_text_1="Confirmed",
        scoring_type="BINARY",
        status="confirmed",
        created_by=sme_user,
    )
    resp = admin_client.delete(f"/api/question-bank/questions/{q.id}/")
    assert resp.status_code == 200
    assert not Question.objects.filter(id=q.id).exists()


# ---------------------------------------------------------------------------
# Tests: Custom role with change permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_custom_role_can_edit_draft_question(custom_client, sme_user):
    """A custom role with question_bank 'change' permission can edit draft questions."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Custom Role Draft",
        question_text_1="Draft for custom role",
        scoring_type="BINARY",
        status="draft",
        created_by=sme_user,
    )
    resp = custom_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Custom role edited"},
        format="json",
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    q.refresh_from_db()
    assert q.question_text_1 == "Custom role edited"


@pytest.mark.django_db
def test_custom_role_cannot_edit_confirmed_question(custom_client, sme_user):
    """A custom role cannot edit a confirmed question (same rules as SME)."""
    q = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Confirmed Title",
        question_text_1="Confirmed",
        scoring_type="BINARY",
        status="confirmed",
        created_by=sme_user,
    )
    resp = custom_client.patch(
        f"/api/question-bank/questions/{q.id}/",
        {"question_text_1": "Trying to edit"},
        format="json",
    )
    assert resp.status_code == 403
