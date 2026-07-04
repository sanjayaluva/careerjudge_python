"""Verify the fix for the bulk options 500 server error when image_file is null.

Reproduces the original error:
  POST /api/question-bank/questions/<qid>/options/bulk/ with payload
  {"options": [{"image_file": null, ...}, ...]}
  used to fail with: 500 server_error due to database IntegrityError.

Root cause: TextField with blank=True but no null=True rejects NULL inserts
when DRF's allow_null=True serializer field passes None through to the model.
After the fix (adding null=True to Question.image, ResponseOption.image_file,
FlashItem.image_file), the bulk options save should succeed.

Django setup is handled by backend/conftest.py (pytest_configure hook), so
this file does NOT need to call django.setup() itself.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.question_bank.models import Question, ResponseOption


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def sme_user(db, roles):
    sme_role = roles["sme"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=sme_role, module="question_bank", action=action)
    return UserFactory(role=sme_role, email="sme-bulk@test.com")


@pytest.fixture
def sme_client(db, sme_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(sme_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


@pytest.fixture
def question(sme_user):
    return Question.objects.create(
        question_type="MCQ_TEXT_IMAGE",
        question_title="Bulk Options Test",
        question_text_1="Bulk options test",
        scoring_type="BINARY",
        created_by=sme_user,
    )


@pytest.mark.django_db
def test_bulk_options_accepts_null_image_file(sme_client, question):
    """Bulk options save must accept image_file=null in the request payload.

    This is the exact payload the frontend sends for text-only MCQ options.
    Before the fix, this returned 500 server_error.
    """
    payload = {
        "options": [
            {
                "sub_question_index": 0,
                "option_type": "TEXT",
                "label": "",
                "text_value": "Option A",
                "image_file": None,
                "is_correct": False,
                "match_pair_id": None,
                "predefined_score": 1,
                "order": 0,
                "correct_answers": [],
            },
            {
                "sub_question_index": 0,
                "option_type": "TEXT",
                "label": "",
                "text_value": "Option B",
                "image_file": None,
                "is_correct": True,
                "match_pair_id": None,
                "predefined_score": 1,
                "order": 1,
                "correct_answers": [],
            },
        ]
    }

    resp = sme_client.post(
        f"/api/question-bank/questions/{question.id}/options/bulk/",
        payload,
        format="json",
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    saved = ResponseOption.objects.filter(question=question)
    assert saved.count() == 2, f"Expected 2 saved, got {saved.count()}. Response: {resp.data}"
    correct = saved.get(text_value="Option B")
    assert correct.is_correct is True


@pytest.mark.django_db
def test_bulk_options_accepts_string_image_file(sme_client, sme_user):
    """Bulk options save must also accept image_file as a base64 data URL string."""
    question = Question.objects.create(
        question_type="MCQ_TEXT_IMAGE_IMG_OPTIONS",
        question_title="Image Option Test",
        question_text_1="Image option test",
        scoring_type="BINARY",
        created_by=sme_user,
    )

    data_url = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    payload = {
        "options": [
            {
                "sub_question_index": 0,
                "option_type": "IMAGE",
                "label": "Image A",
                "text_value": "",
                "image_file": data_url,
                "is_correct": True,
                "match_pair_id": None,
                "predefined_score": 1,
                "order": 0,
                "correct_answers": [],
            }
        ]
    }

    resp = sme_client.post(
        f"/api/question-bank/questions/{question.id}/options/bulk/",
        payload,
        format="json",
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    saved = ResponseOption.objects.filter(question=question)
    assert saved.count() == 1, f"Expected 1 saved, got {saved.count()}. Response: {resp.data}"
    saved_opt = saved.first()
    assert saved_opt.label == "Image A"
    assert saved_opt.image_file == data_url


@pytest.mark.django_db
def test_response_option_image_field_allows_null():
    """The ResponseOption.image_file field must allow NULL at the DB level."""
    field = ResponseOption._meta.get_field("image_file")
    assert field.null is True, "ResponseOption.image_file must have null=True"
    assert field.blank is True, "ResponseOption.image_file must have blank=True"


@pytest.mark.django_db
def test_question_image_field_allows_null():
    """The Question.image field must allow NULL at the DB level."""
    field = Question._meta.get_field("image")
    assert field.null is True, "Question.image must have null=True"
    assert field.blank is True, "Question.image must have blank=True"
