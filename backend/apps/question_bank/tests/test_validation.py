"""Tests for question configuration validation.

Covers the rules in apps/question_bank/validation.py for every question type.
Critical regression: a hotspot question saved without any hotspot_area must
produce a validation error (issue: "created a hotspot question without
options and it saved as normal").
"""

import pytest

from apps.question_bank.models import Question
from apps.question_bank.validation import (
    question_is_ready_for_review,
    validate_question_config,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_question(**overrides) -> Question:
    """Create a minimal draft question with sensible defaults."""
    defaults = {
        "question_type": "MCQ_TEXT_MULTI",
        "question_title": "T",
        "question_text_1": "Q?",
        "scoring_type": "ALL_OR_NOTHING",
        "status": "draft",
    }
    defaults.update(overrides)
    return Question.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Common validations
# ---------------------------------------------------------------------------


def test_missing_title_blocks_review():
    q = _make_question(question_title="")
    errors = validate_question_config(q)
    assert any("title" in e.lower() for e in errors)
    assert question_is_ready_for_review(q) is False


def test_missing_question_text_blocks_review():
    q = _make_question(question_text_1="")
    errors = validate_question_config(q)
    assert any("question text" in e.lower() for e in errors)


def test_missing_scoring_type_blocks_review():
    q = _make_question(scoring_type="")
    errors = validate_question_config(q)
    assert any("scoring" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# MCQ
# ---------------------------------------------------------------------------


def test_mcq_with_two_options_and_one_correct_is_valid():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="MCQ_TEXT_MULTI")
    ResponseOption.objects.create(question=q, order=0, text_value="A", is_correct=True)
    ResponseOption.objects.create(question=q, order=1, text_value="B", is_correct=False)
    assert validate_question_config(q) == []
    assert question_is_ready_for_review(q) is True


def test_mcq_with_fewer_than_two_options_is_invalid():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="MCQ_TEXT_MULTI")
    ResponseOption.objects.create(question=q, order=0, text_value="A", is_correct=True)
    errors = validate_question_config(q)
    assert any("at least 2 options" in e for e in errors)


def test_mcq_with_no_correct_option_is_invalid():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="MCQ_TEXT_MULTI")
    ResponseOption.objects.create(question=q, order=0, text_value="A", is_correct=False)
    ResponseOption.objects.create(question=q, order=1, text_value="B", is_correct=False)
    errors = validate_question_config(q)
    assert any("correct" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Hotspot — regression for "hotspot saved without options/areas"
# ---------------------------------------------------------------------------


def test_hotspot_single_without_areas_is_invalid():
    """Regression: hotspot saved with no hotspot_area must fail validation."""
    q = _make_question(
        question_type="HOTSPOT_SINGLE",
        image="http://example.com/img.png",
        image_width=800,
        image_height=600,
    )
    errors = validate_question_config(q)
    assert any("hotspot area" in e.lower() for e in errors)
    assert question_is_ready_for_review(q) is False


def test_hotspot_single_without_correct_area_is_invalid():
    from apps.question_bank.models import HotspotArea

    q = _make_question(
        question_type="HOTSPOT_SINGLE",
        image="http://example.com/img.png",
        image_width=800,
        image_height=600,
    )
    HotspotArea.objects.create(
        question=q,
        x=10,
        y=10,
        width_px=50,
        height_px=50,
        is_correct=False,
    )
    errors = validate_question_config(q)
    assert any("correct hotspot" in e.lower() for e in errors)


def test_hotspot_single_with_one_correct_area_is_valid():
    from apps.question_bank.models import HotspotArea

    q = _make_question(
        question_type="HOTSPOT_SINGLE",
        image="http://example.com/img.png",
        image_width=800,
        image_height=600,
    )
    HotspotArea.objects.create(
        question=q,
        x=10,
        y=10,
        width_px=50,
        height_px=50,
        is_correct=True,
    )
    assert validate_question_config(q) == []


def test_hotspot_multi_requires_two_correct_areas():
    from apps.question_bank.models import HotspotArea

    q = _make_question(
        question_type="HOTSPOT_MULTI",
        image="http://example.com/img.png",
        image_width=800,
        image_height=600,
    )
    HotspotArea.objects.create(
        question=q,
        x=10,
        y=10,
        width_px=50,
        height_px=50,
        is_correct=True,
    )
    errors = validate_question_config(q)
    assert any("2 correct" in e for e in errors)


def test_hotspot_without_image_is_invalid():
    q = _make_question(question_type="HOTSPOT_SINGLE", image_width=800, image_height=600)
    errors = validate_question_config(q)
    assert any("image" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# FITB
# ---------------------------------------------------------------------------


def test_fitb_without_correct_answers_is_invalid():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="FITB_TEXT")
    ResponseOption.objects.create(question=q, order=0, text_value="Field 1")
    errors = validate_question_config(q)
    assert any("correct answers" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------


def test_match_requires_two_pairs():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="MATCH_FOLLOWING")
    ResponseOption.objects.create(
        question=q, order=0, option_type="MATCH_A", text_value="A1", match_pair_id=1
    )
    ResponseOption.objects.create(
        question=q, order=1, option_type="MATCH_B", text_value="B1", match_pair_id=1
    )
    errors = validate_question_config(q)
    assert any("group a" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Rank
# ---------------------------------------------------------------------------


def test_rank_requires_two_options():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="RANK_SIMPLE")
    ResponseOption.objects.create(question=q, order=0, option_type="RANK", text_value="1")
    errors = validate_question_config(q)
    assert any("at least 2 options" in e for e in errors)


# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------


def test_rating_requires_two_points():
    q = _make_question(question_type="STANDARD_RATING_SCALE", rating_scale_points=1)
    errors = validate_question_config(q)
    assert any("rating_scale_points" in e for e in errors)


# ---------------------------------------------------------------------------
# Forced Choice
# ---------------------------------------------------------------------------


def test_forced_choice_requires_two_options_with_score():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="FORCED_CHOICE_SINGLE_LEVEL")
    ResponseOption.objects.create(
        question=q, order=0, option_type="FORCED_CHOICE", text_value="A", predefined_score=1
    )
    errors = validate_question_config(q)
    assert any("at least 2 options" in e for e in errors)


def test_forced_choice_option_without_score_is_invalid():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="FORCED_CHOICE_SINGLE_LEVEL")
    ResponseOption.objects.create(
        question=q, order=0, option_type="FORCED_CHOICE", text_value="A", predefined_score=0
    )
    ResponseOption.objects.create(
        question=q, order=1, option_type="FORCED_CHOICE", text_value="B", predefined_score=2
    )
    errors = validate_question_config(q)
    assert any("predefined_score" in e for e in errors)


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------


def test_grid_requires_drag_pool_option():
    q = _make_question(question_type="GRID_LIST_SELECTION", grid_rows=2, grid_cols=2)
    errors = validate_question_config(q)
    assert any("drag_pool" in e.lower() or "cell content" in e.lower() for e in errors)
