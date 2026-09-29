"""Partial-credit scoring for 2b / 2c / 2d (Report 7 #24/#25/#26).

Scoring spec (00_scoring_rules PARTIAL): each item +1, no negative marking;
recall types score each flashed item recalled, in any order.
"""

import pytest

from apps.assessment.scoring import _get_max_score, score_question
from apps.question_bank.models import CorrectAnswer, FlashItem, Question, ResponseOption

pytestmark = pytest.mark.django_db


def _fitb(qtype, fields, scoring_type="BINARY", **kw):
    """`fields` = list of accepted-answer lists, one per answer field."""
    q = Question.objects.create(
        question_type=qtype,
        question_title=qtype,
        question_text_1="q",
        status="confirmed",
        scoring_type=scoring_type,
        **kw,
    )
    for i, accepted in enumerate(fields):
        opt = ResponseOption.objects.create(question=q, label=f"Field {i + 1}", order=i)
        for text in accepted:
            CorrectAnswer.objects.create(response_option=opt, answer_text=text)
    return q


def _flash(q, values, item_type="TEXT"):
    for i, v in enumerate(values):
        FlashItem.objects.create(question=q, item_type=item_type, text_value=v, order=i)


def test_multi_field_scores_per_field_even_if_saved_as_binary():
    # The client's SMQFM 01.01: saved with "Binary Scoring (0 or 1)".
    q = _fitb("FITB_MULTI_FIELD", [["keep"], ["pay"], ["pass"]], scoring_type="BINARY")
    assert score_question(q, {"answers": ["keep", "pay", "pass"]}) == (3.0, 3.0)
    assert score_question(q, {"answers": ["keep", "x", "pass"]}) == (2.0, 3.0)
    assert _get_max_score(q) == 3.0


WORDS = ["Socket", "Chair", "Pump", "Tank", "Pancake", "Hammer", "Grill", "Bracelet"]
WORDS += ["Enclosure", "Fridge"]


def test_word_flash_recall_scores_each_item_any_order():
    # The client's SMQFI 01.01: 10 flash words, a single answer field ("Socket").
    q = _fitb("FITB_WORD_FLASH_MULTI", [["Socket"]], flash_display_count=10)
    _flash(q, WORDS)
    shuffled = list(reversed(WORDS))
    assert score_question(q, {"answers": shuffled}) == (10.0, 10.0)
    # Wrong entries score 0 (no negative); duplicates count once; case-insensitive.
    assert score_question(q, {"answers": ["socket", "SOCKET", "Banana", "pump"]}) == (2.0, 10.0)
    assert _get_max_score(q) == 10.0


def test_recall_max_is_the_number_of_items_flashed():
    q = _fitb("FITB_WORD_FLASH_MULTI", [], flash_display_count=5)
    _flash(q, WORDS)
    assert score_question(q, {"answers": WORDS}) == (5.0, 5.0)


def test_image_flash_recall_uses_each_image_name():
    # 2d: images carry their accepted name(s) in the aligned answer field.
    names = [["Banana"], ["Bulb"], ["Book"], ["Boat", "Ship"]]
    q = _fitb("FITB_IMAGE_FLASH_MULTI", names, flash_display_count=4)
    _flash(q, ["", "", "", ""], item_type="IMAGE")
    assert score_question(q, {"answers": ["ship", "Book", "Bulb", "Banana"]}) == (4.0, 4.0)
    assert score_question(q, {"answers": ["Boat", "Ship"]}) == (1.0, 4.0)


def test_type_fixed_scoring_is_applied_on_save():
    q = _fitb("FITB_MULTI_FIELD", [["a"]], scoring_type="BINARY")
    q.refresh_from_db()
    assert q.scoring_type == "PARTIAL"


def test_image_flash_requires_a_name_per_image():
    from apps.question_bank.validation import validate_question_config

    q = _fitb("FITB_IMAGE_FLASH_MULTI", [["Banana"]], flash_interval_ms=500)
    _flash(q, ["", ""], item_type="IMAGE")
    errors = validate_question_config(q)
    assert any("Flash image #2 has no accepted name" in e for e in errors), errors

    # 2c words need no answer fields at all — the flashed word is the answer.
    w = _fitb("FITB_WORD_FLASH_MULTI", [], flash_interval_ms=500)
    _flash(w, ["Apple"])
    assert validate_question_config(w) == []


def test_rating_legend_dedupe_migration_keeps_latest_per_point():
    from importlib import import_module

    from django.apps import apps as django_apps

    q = Question.objects.create(
        question_type="STANDARD_RATING_SCALE",
        question_title="r",
        question_text_1="r",
        status="confirmed",
        rating_scale_points=3,
    )
    for rnd in ("old", "new"):
        for n in (1, 2, 3):
            ResponseOption.objects.create(question=q, label=f"Point {n}", text_value=f"{rnd}{n}")
    mig = import_module("apps.question_bank.migrations.0021_dedupe_rating_legends")
    mig.forwards(django_apps, None)
    legends = sorted(q.options.values_list("label", "text_value"))
    assert legends == [("Point 1", "new1"), ("Point 2", "new2"), ("Point 3", "new3")]
