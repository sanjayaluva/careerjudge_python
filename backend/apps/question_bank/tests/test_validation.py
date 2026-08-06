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


def test_hotspot_single_with_only_one_correct_area_is_invalid():
    """Regression: a single hotspot area (which defaults to is_correct=True)
    must fail validation because the candidate has no distractor to avoid.
    Without a distractor, clicking anywhere inside the area = correct and
    clicking anywhere outside = wrong — the question has zero discrimination.
    """
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
        is_correct=True,  # default
    )
    errors = validate_question_config(q)
    assert any("distractor" in e.lower() for e in errors)
    assert question_is_ready_for_review(q) is False


def test_hotspot_single_with_one_correct_and_one_distractor_is_valid():
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
    HotspotArea.objects.create(
        question=q,
        x=200,
        y=200,
        width_px=50,
        height_px=50,
        is_correct=False,
    )
    assert validate_question_config(q) == []
    assert question_is_ready_for_review(q) is True


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
    # 1 correct, 0 incorrect — should produce BOTH errors
    assert any("2 correct" in e for e in errors)
    assert any("distractor" in e.lower() for e in errors)


def test_hotspot_multi_with_two_correct_and_one_distractor_is_valid():
    from apps.question_bank.models import HotspotArea

    q = _make_question(
        question_type="HOTSPOT_MULTI",
        image="http://example.com/img.png",
        image_width=800,
        image_height=600,
    )
    HotspotArea.objects.create(question=q, x=10, y=10, width_px=50, height_px=50, is_correct=True)
    HotspotArea.objects.create(question=q, x=100, y=100, width_px=50, height_px=50, is_correct=True)
    HotspotArea.objects.create(
        question=q, x=200, y=200, width_px=50, height_px=50, is_correct=False
    )
    assert validate_question_config(q) == []


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
    ResponseOption.objects.create(
        question=q, order=0, option_type="RANK", text_value="1", section_tag="S1"
    )
    errors = validate_question_config(q)
    assert any("at least 2 options" in e for e in errors)


def test_rank_requires_distinct_section_tags():
    """Report 2 §1: each option tagged to a different section."""
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="RANK_SIMPLE")
    # Two options share the same tag → invalid
    ResponseOption.objects.create(
        question=q, order=0, option_type="RANK", text_value="1", section_tag="S1"
    )
    ResponseOption.objects.create(
        question=q, order=1, option_type="RANK", text_value="2", section_tag="S1"
    )
    errors = validate_question_config(q)
    assert any("DIFFERENT section" in e for e in errors)


def test_rank_requires_every_option_to_have_a_tag():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="RANK_SIMPLE")
    ResponseOption.objects.create(
        question=q, order=0, option_type="RANK", text_value="1", section_tag="S1"
    )
    ResponseOption.objects.create(
        question=q, order=1, option_type="RANK", text_value="2", section_tag=""
    )
    errors = validate_question_config(q)
    assert any("section_tag" in e for e in errors)


def test_rank_with_distinct_tags_is_valid():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="RANK_SIMPLE")
    for i, tag in enumerate(["S1", "S2", "S3", "S4"], start=0):
        ResponseOption.objects.create(
            question=q, order=i, option_type="RANK", text_value=str(i), section_tag=tag
        )
    errors = validate_question_config(q)
    assert not any("section" in e.lower() for e in errors)


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
        question=q, order=0, option_type="FORCED_CHOICE", text_value="A", section_tag="S1"
    )
    errors = validate_question_config(q)
    assert any("at least 2 options" in e for e in errors)


def test_forced_choice_same_section_pair_is_invalid():
    """Report 2 §3: two options from the same section cannot be paired."""
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="FORCED_CHOICE_SINGLE_LEVEL")
    ResponseOption.objects.create(
        question=q, order=0, option_type="FORCED_CHOICE", text_value="A", section_tag="S1"
    )
    ResponseOption.objects.create(
        question=q, order=1, option_type="FORCED_CHOICE", text_value="B", section_tag="S1"
    )
    errors = validate_question_config(q)
    assert any("DIFFERENT sections" in e for e in errors)


def test_forced_choice_selection_must_exceed_non_selection():
    """Report 2 §3 rule: selection_score > non_selection_score >= 0."""
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="FORCED_CHOICE_SINGLE_LEVEL")
    # selection (1) is NOT greater than non_selection (2) → invalid
    ResponseOption.objects.create(
        question=q,
        order=0,
        option_type="FORCED_CHOICE",
        text_value="A",
        section_tag="S1",
        selection_score=1.0,
        non_selection_score=2.0,
    )
    ResponseOption.objects.create(
        question=q,
        order=1,
        option_type="FORCED_CHOICE",
        text_value="B",
        section_tag="S2",
        selection_score=3.0,
        non_selection_score=0.0,
    )
    errors = validate_question_config(q)
    assert any("selection_score" in e and "greater than" in e for e in errors)


def test_forced_choice_negative_non_selection_is_invalid():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="FORCED_CHOICE_SINGLE_LEVEL")
    ResponseOption.objects.create(
        question=q,
        order=0,
        option_type="FORCED_CHOICE",
        text_value="A",
        section_tag="S1",
        selection_score=2.0,
        non_selection_score=-1.0,
    )
    ResponseOption.objects.create(
        question=q,
        order=1,
        option_type="FORCED_CHOICE",
        text_value="B",
        section_tag="S2",
        selection_score=3.0,
        non_selection_score=0.0,
    )
    errors = validate_question_config(q)
    assert any("negative" in e for e in errors)


def test_forced_choice_with_distinct_tags_and_valid_scores_is_valid():
    from apps.question_bank.models import ResponseOption

    q = _make_question(question_type="FORCED_CHOICE_SINGLE_LEVEL")
    ResponseOption.objects.create(
        question=q,
        order=0,
        option_type="FORCED_CHOICE",
        text_value="A",
        section_tag="S1",
        selection_score=2.0,
        non_selection_score=0.0,
    )
    ResponseOption.objects.create(
        question=q,
        order=1,
        option_type="FORCED_CHOICE",
        text_value="B",
        section_tag="S2",
        selection_score=3.0,
        non_selection_score=1.0,
    )
    errors = validate_question_config(q)
    assert errors == []


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------


def test_grid_requires_drag_pool_option():
    q = _make_question(question_type="GRID_LIST_SELECTION", grid_rows=2, grid_cols=2)
    errors = validate_question_config(q)
    assert any("drag_pool" in e.lower() or "cell content" in e.lower() for e in errors)
