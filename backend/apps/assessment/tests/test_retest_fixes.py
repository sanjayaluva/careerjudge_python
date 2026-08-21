"""Regression tests for the Post-Updation Retesting Report (Normal Qn Types).

Each test reproduces a scoring case from the client's retest screenshots:
  - 1c audio multi: sub-question max must count ONLY that sub-question's
    correct options (was 1/3, 3/5 — pooled all-sub-question options).
  - 1g passage multi: 2 correct per sub-q -> 2/2 (was 2/6).
  - 1h image display multi: 2 correct -> 2/2 (was 1/2).
  - 1f image flash multi: 3 correct all selected -> 3/3 and score 3 (was 0/1).
  - 2a FITB single: correct answer -> 1/1 (was 0/1).
  - 2b FITB multi-field: 3 correct -> 3/3 (was 0/1).
  - 2d FITB image flash: 10 any-order correct -> 10/10 (was 0/1).
  - 3 Match with 3 Group-B distractors: 6 pairs -> 6/6 (was 0.0/7.5).
"""

import pytest

from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.assessment.scoring import score_question
from apps.question_bank.models import CorrectAnswer, Question, ResponseOption

pytestmark = pytest.mark.django_db


def _mk_q(user, qtype, stype, **extra):
    defaults = {
        "question_type": qtype,
        "question_title": "T",
        "question_text_1": "T",
        "scoring_type": stype,
        "status": "confirmed",
        "created_by": user,
    }
    defaults.update(extra)
    return Question.objects.create(**defaults)


@pytest.fixture(autouse=True)
def _roles(db):
    get_or_create_default_roles()


@pytest.fixture
def user(db):
    return UserFactory.create(role=get_or_create_default_roles()["individual"])


def _mk_opt(q, sqi, correct, n, **kw):
    return ResponseOption.objects.create(
        question=q,
        sub_question_index=sqi,
        option_type=kw.pop("option_type", "TEXT"),
        text_value=kw.pop("text_value", f"opt{n}"),
        is_correct=correct,
        order=n,
        **kw,
    )


def test_audio_multi_subq0_max_counts_only_its_correct(user):
    """Retest 1c: 3 sub-questions, 1 correct each. Sub-q 1 (index 0) must be
    1/1 — the index-0 filter skip previously pooled ALL correct options (1/3)."""
    q = _mk_q(user, "MCQ_AUDIO_MULTI", "BINARY")
    ids = []
    for sqi, n_correct in ((0, 1), (1, 1), (2, 1)):
        sq_correct = [_mk_opt(q, sqi, True, i) for i in range(n_correct)]
        _mk_opt(q, sqi, False, 10)
        _mk_opt(q, sqi, False, 11)
        ids.append([o.id for o in sq_correct])
    score, mx = score_question(q, {"selected_option_ids": ids[0]}, 0)
    assert (score, mx) == (1.0, 1.0)
    score, mx = score_question(q, {"selected_option_ids": ids[2]}, 2)
    assert (score, mx) == (1.0, 1.0)


def test_audio_multi_multianswer_subq_max(user):
    """Retest 1c MCAM 01.02: sub-q with 3 correct -> 3/3 (was 3/5)."""
    q = _mk_q(user, "MCQ_AUDIO_MULTI", "BINARY")
    correct0 = [_mk_opt(q, 0, True, i) for i in range(3)]
    [_mk_opt(q, 0, False, i) for i in range(10, 13)]
    _mk_opt(q, 1, True, 1)
    _mk_opt(q, 1, False, 2)
    sel = [o.id for o in correct0]
    score, mx = score_question(q, {"selected_option_ids": sel}, 0)
    assert (score, mx) == (3.0, 3.0)


def test_passage_multi_subq3_two_correct(user):
    """Retest 1g: each sub-q has 2 correct; sub-q 3 -> 2/2 (was 2/6)."""
    q = _mk_q(user, "MCQ_PASSAGE_DISPLAY_MULTI", "BINARY")
    per_sq_correct = []
    for sqi in (0, 1, 2):
        cs = [_mk_opt(q, sqi, True, i) for i in range(2)]
        _mk_opt(q, sqi, False, 10)
        per_sq_correct.append([o.id for o in cs])
    score, mx = score_question(q, {"selected_option_ids": per_sq_correct[2]}, 2)
    assert (score, mx) == (2.0, 2.0)


def test_image_display_multi_two_correct(user):
    """Retest 1h: 2 correct, both selected -> 2/2 (was 1/2)."""
    q = _mk_q(user, "MCQ_IMAGE_DISPLAY_MULTI", "BINARY")
    cs = [_mk_opt(q, 0, True, i) for i in range(2)]
    _mk_opt(q, 0, False, 10)
    score, mx = score_question(q, {"selected_option_ids": [o.id for o in cs]}, 0)
    assert (score, mx) == (2.0, 2.0)


def test_fitb_single_correct_scores_one(user):
    """Retest 2a: single-field FITB correct answer -> 1/1 (was 0/1)."""
    q = _mk_q(user, "FITB_SINGLE", "BINARY_FUZZY")
    o = _mk_opt(q, 0, True, 1)
    CorrectAnswer.objects.create(response_option=o, answer_text="Paris")
    score, mx = score_question(q, {"answers": ["Paris"]}, 0)
    assert (score, mx) == (1.0, 1.0)


def test_fitb_multi_field_three_correct(user):
    """Retest 2b: 3 fields, 3 correct answers -> 3/3 (was 0/1)."""
    q = _mk_q(user, "FITB_MULTI_FIELD", "PARTIAL")
    for i, ans in enumerate(["a", "b", "c"]):
        o = _mk_opt(q, 0, True, i)
        CorrectAnswer.objects.create(response_option=o, answer_text=ans)
    score, mx = score_question(q, {"answers": ["a", "b", "c"]}, 0)
    assert (score, mx) == (3.0, 3.0)


def test_fitb_flash_ten_any_order(user):
    """Retest 2d: 10 flash images, any-order entries -> 10/10 (was 0/1)."""
    q = _mk_q(user, "FITB_IMAGE_FLASH_MULTI", "PARTIAL")
    for i in range(10):
        o = _mk_opt(q, 0, True, i)
        CorrectAnswer.objects.create(response_option=o, answer_text=f"img{i}")
    answers = [f"img{i}" for i in range(10)][::-1]  # reversed order
    score, mx = score_question(q, {"answers": answers}, 0)
    assert (score, mx) == (10.0, 10.0)


def test_match_with_distractors_six_pairs(user):
    """Retest 3: 6 pairs + 3 Group-B distractors -> 6/6 (was 0.0/7.5)."""
    q = _mk_q(user, "MATCH_FOLLOWING", "PARTIAL")
    a_ids, b_ids = [], []
    for i in range(1, 7):
        a = ResponseOption.objects.create(
            question=q, option_type="MATCH_A", text_value=f"A{i}", match_pair_id=i, order=i
        )
        b = ResponseOption.objects.create(
            question=q, option_type="MATCH_B", text_value=f"B{i}", match_pair_id=i, order=i + 10
        )
        a_ids.append(a.id)
        b_ids.append(b.id)
    for d in range(3):
        ResponseOption.objects.create(
            question=q,
            option_type="MATCH_DUMMY",
            text_value=f"D{d}",
            order=50 + d,
        )
    pairs = [{"a_id": a_ids[i], "b_id": b_ids[i]} for i in range(6)]
    score, mx = score_question(q, {"pairs": pairs}, 0)
    assert (score, mx) == (6.0, 6.0)
