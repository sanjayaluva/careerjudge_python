"""Verify the fix for the image validation error.

Reproduces the original error:
  POST /api/question-bank/questions/ with image="data:image/png;base64,..."
  used to fail with: "image: The submitted data was not a file. Check the
  encoding type on the form."

After the fix (ImageField -> TextField on Question.image, and explicit
CharField override in QuestionCreateSerializer), the request should succeed.

Django setup is handled by backend/conftest.py (pytest_configure hook), so
this file does NOT need to call django.setup() itself.
"""

import pytest
from rest_framework.test import APIRequestFactory

from apps.accounts.tests.factories import UserFactory
from apps.question_bank.models import Question
from apps.question_bank.serializers import QuestionCreateSerializer


@pytest.mark.django_db
def test_question_create_accepts_base64_data_url_image():
    """The QuestionCreateSerializer must accept a base64 data URL string for image."""
    sme = UserFactory()
    # A tiny 1x1 transparent PNG as a base64 data URL
    data_url = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    payload = {
        "question_type": "MCQ_TEXT_IMAGE",
        "question_text_1": "What is 2 + 2?",
        "scoring_type": "BINARY",
        "difficulty_level": "Easy",
        "image": data_url,
    }
    factory = APIRequestFactory()
    request = factory.post("/api/question-bank/questions/", payload, format="json")
    request.user = sme
    serializer = QuestionCreateSerializer(data=payload, context={"request": request})
    assert serializer.is_valid(), f"Serializer should be valid, errors: {serializer.errors}"
    question = serializer.save(created_by=sme)
    assert question.id is not None
    assert question.image == data_url
    assert question.image.startswith("data:image/png;base64,")


@pytest.mark.django_db
def test_question_create_accepts_external_url_image():
    """The QuestionCreateSerializer must accept an external URL string for image."""
    sme = UserFactory()
    external_url = "https://example.com/images/question-1.png"
    payload = {
        "question_type": "MCQ_TEXT_IMAGE",
        "question_text_1": "What is 3 + 3?",
        "scoring_type": "BINARY",
        "image": external_url,
    }
    factory = APIRequestFactory()
    request = factory.post("/api/question-bank/questions/", payload, format="json")
    request.user = sme
    serializer = QuestionCreateSerializer(data=payload, context={"request": request})
    assert serializer.is_valid(), f"Serializer should be valid, errors: {serializer.errors}"
    question = serializer.save(created_by=sme)
    assert question.image == external_url


@pytest.mark.django_db
def test_question_create_accepts_no_image():
    """The QuestionCreateSerializer must accept no image at all (image is optional)."""
    sme = UserFactory()
    payload = {
        "question_type": "MCQ_TEXT_IMAGE",
        "question_text_1": "What is 4 + 4?",
        "scoring_type": "BINARY",
    }
    factory = APIRequestFactory()
    request = factory.post("/api/question-bank/questions/", payload, format="json")
    request.user = sme
    serializer = QuestionCreateSerializer(data=payload, context={"request": request})
    assert serializer.is_valid(), f"Serializer should be valid, errors: {serializer.errors}"
    question = serializer.save(created_by=sme)
    assert question.image == ""  # TextField with blank=True defaults to ""


@pytest.mark.django_db
def test_existing_question_image_field_is_text():
    """The Question.image field is now a TextField — verify via the model class."""
    field = Question._meta.get_field("image")
    # Internal type for TextField is "TextField"
    assert (
        field.get_internal_type() == "TextField"
    ), f"Expected TextField, got {field.get_internal_type()}"
