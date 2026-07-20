"""Tests for the Psychometric Analysis computation engine.

Covers SRS 02_psychometric_analysis_computation.json:
  - Item Difficulty Index (MCQ): IDI, TDI, BDI, DDI (SRS §2)
  - Item Difficulty Index (non-MCQ): mean-based formulas (SRS §3)
  - Item Discrimination Index (MCQ) (SRS §4)
  - Item Total Correlation Index (non-MCQ) (SRS §5)

The engine pulls data from QuestionAttempt records across completed
AssessmentSessions. These tests build synthetic attempts with known
score distributions and verify the computed indices match the SRS
formulas.
"""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import (
    Assessment,
    AssessmentSession,
    QuestionAttempt,
)
from apps.assessment.tests.factories import get_or_create_role
from apps.question_bank.models import Category, Question
from apps.question_bank.psychometrics import run_psychometric_analysis

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_question(qtype="MCQ_TEXT_MULTI", scoring_type="BINARY"):
    """Create a confirmed question with a category."""
    cat = Category.objects.create(name="Test Cat")
    return Question.objects.create(
        category=cat,
        question_type=qtype,
        question_title="T",
        question_text_1="Q?",
        scoring_type=scoring_type,
        status="confirmed",
    )


def _make_completed_session(assessment, candidate, total_score):
    """Create a completed session with the given total_score."""
    return AssessmentSession.objects.create(
        assessment=assessment,
        candidate=candidate,
        status="completed",
        total_score=float(total_score),
        max_score=10.0,
        percentage=(float(total_score) / 10.0) * 100,
    )


def _make_attempt(session, question, score, max_score=1.0):
    """Create an 'attempted' QuestionAttempt with the given score."""
    return QuestionAttempt.objects.create(
        session=session,
        question=question,
        status="attempted",
        score=float(score),
        max_score=float(max_score),
    )


def _make_candidate(email):
    return UserFactory.create(role=get_or_create_role("individual", is_system=True), email=email)


# ---------------------------------------------------------------------------
# Sanity: insufficient data
# ---------------------------------------------------------------------------


def test_insufficient_data_returns_error():
    """A question with 0 or 1 attempts returns an error result and the
    Question's indices remain null."""
    q = _make_question()
    assessment = Assessment.objects.create(title="A", status="published")
    # 1 candidate, 1 attempt
    c = _make_candidate("c1@test.com")
    s = _make_completed_session(assessment, c, total_score=5)
    _make_attempt(s, q, score=1.0)

    result = run_psychometric_analysis(q)
    assert result.error is not None
    assert "Insufficient data" in result.error
    assert result.item_difficulty_index is None
    assert result.discrimination_index is None
    # Persisted on Question too
    q.refresh_from_db()
    assert q.item_difficulty_index is None
    assert q.psychometric_analyzed_at is not None  # timestamp set even on failure


# ---------------------------------------------------------------------------
# MCQ Item Difficulty Index (SRS §2)
# ---------------------------------------------------------------------------


def test_mcq_idi_is_correct_count_divided_by_total():
    """10 candidates, 6 correct -> IDI = 0.6."""
    q = _make_question(qtype="MCQ_TEXT_MULTI", scoring_type="BINARY")
    assessment = Assessment.objects.create(title="A", status="published")
    # 6 correct (score=1), 4 incorrect (score=0)
    scores = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
    total_scores = [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    for i, (s, ts) in enumerate(zip(scores, total_scores, strict=False)):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s)

    result = run_psychometric_analysis(q)
    assert result.n_candidates == 10
    assert result.item_difficulty_index == pytest.approx(0.6, abs=0.001)


def test_mcq_tdi_bdi_use_top_bottom_27_percent():
    """With 10 candidates, top 27% = top 3 (27% of 10 = 2.7, rounds to 3).

    Setup (sorted by total_score descending):
      Rank 1: total=9, target=1 (correct)
      Rank 2: total=8, target=1
      Rank 3: total=7, target=1
      Rank 4: total=6, target=1
      Rank 5: total=5, target=1
      Rank 6: total=4, target=1
      Rank 7: total=3, target=0
      Rank 8: total=2, target=0
      Rank 9: total=1, target=0
      Rank 10: total=0, target=0

    Top 3 (ranks 1-3): all correct -> TDI = 3/3 = 1.0
    Bottom 3 (ranks 8-10): all incorrect -> BDI = 0/3 = 0.0
    DDI = 1.0 - 0.0 = 1.0
    """
    q = _make_question()
    assessment = Assessment.objects.create(title="A", status="published")
    # (target_score, total_score) pairs
    pairs = [
        (1, 9),
        (1, 8),
        (1, 7),
        (1, 6),
        (1, 5),
        (1, 4),
        (0, 3),
        (0, 2),
        (0, 1),
        (0, 0),
    ]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s)

    result = run_psychometric_analysis(q)
    assert result.top_group_difficulty_index == pytest.approx(1.0, abs=0.001)
    assert result.bottom_group_difficulty_index == pytest.approx(0.0, abs=0.001)
    assert result.difference_difficulty_index == pytest.approx(1.0, abs=0.001)


def test_mcq_partial_credit_treated_as_correct_at_50_percent():
    """For PARTIAL scoring, score >= 50% of max_score counts as 'correct'.

    Setup: 4 candidates, max_score=2 each:
      c1: score=2 (100% -> correct)
      c2: score=1 (50% -> correct)
      c3: score=0.5 (25% -> incorrect)
      c4: score=0 (0% -> incorrect)
    IDI = 2/4 = 0.5
    """
    q = _make_question(qtype="MCQ_TEXT_MULTI", scoring_type="PARTIAL")
    assessment = Assessment.objects.create(title="A", status="published")
    pairs = [(2.0, 10), (1.0, 8), (0.5, 5), (0.0, 2)]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s, max_score=2.0)

    result = run_psychometric_analysis(q)
    assert result.item_difficulty_index == pytest.approx(0.5, abs=0.001)


# ---------------------------------------------------------------------------
# MCQ Discrimination Index (SRS §4)
# ---------------------------------------------------------------------------


def test_mcq_discrimination_index_positive_when_top_performers_correct():
    """When top performers get the question right and bottom performers
    get it wrong, discrimination should be positive.

    Setup (perfect separation):
      Top 3: target correct (score=1), high total scores
      Bottom 3: target incorrect (score=0), low total scores
      Middle 4: mixed
    """
    q = _make_question()
    assessment = Assessment.objects.create(title="A", status="published")
    # 10 candidates: top 5 correct with high totals, bottom 5 incorrect with low totals
    pairs = [
        (1, 10),
        (1, 9),
        (1, 8),
        (1, 7),
        (1, 6),
        (0, 5),
        (0, 4),
        (0, 3),
        (0, 2),
        (0, 1),
    ]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s)

    result = run_psychometric_analysis(q)
    assert result.discrimination_index is not None
    assert result.discrimination_index > 0  # top performers did better


def test_mcq_discrimination_index_zero_when_no_variance():
    """If all candidates have the same total score, SD=0 -> discrimination None."""
    q = _make_question()
    assessment = Assessment.objects.create(title="A", status="published")
    pairs = [(1, 5), (0, 5), (1, 5), (0, 5)]  # all total_score = 5
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s)

    result = run_psychometric_analysis(q)
    assert result.discrimination_index is None  # SD=0


def test_mcq_discrimination_index_none_when_all_correct():
    """If every candidate got the target correct, N2=0 -> discrimination None."""
    q = _make_question()
    assessment = Assessment.objects.create(title="A", status="published")
    pairs = [(1, 10), (1, 9), (1, 8), (1, 7)]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s)

    result = run_psychometric_analysis(q)
    assert result.discrimination_index is None


# ---------------------------------------------------------------------------
# Non-MCQ Item Difficulty Index (SRS §3)
# ---------------------------------------------------------------------------


def test_non_mcq_idi_uses_mean_score_divided_by_max():
    """Non-MCQ IDI = (sum target / N) / max_score.

    Setup: 4 candidates, max_score=10:
      scores = [10, 8, 6, 4] -> mean = 7 -> IDI = 7/10 = 0.7
    """
    q = _make_question(qtype="FITB_TEXT", scoring_type="PARTIAL")
    assessment = Assessment.objects.create(title="A", status="published")
    pairs = [(10, 10), (8, 8), (6, 6), (4, 4)]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s, max_score=10.0)

    result = run_psychometric_analysis(q)
    assert result.item_difficulty_index == pytest.approx(0.7, abs=0.001)
    # Non-MCQ -> discrimination is None, item_total_correlation is computed
    assert result.discrimination_index is None
    assert result.item_total_correlation is not None


def test_non_mcq_tdi_bdi_use_top_bottom_27_percent():
    """Non-MCQ TDI/BDI use mean target score in top/bottom 27% divided by max."""
    q = _make_question(qtype="FITB_TEXT", scoring_type="PARTIAL")
    assessment = Assessment.objects.create(title="A", status="published")
    # Sorted by total_score descending, target_score is correlated
    # 10 candidates, top 3 (ranks 1-3): target scores [10, 9, 8] -> mean 9 -> TDI = 9/10 = 0.9
    # Bottom 3 (ranks 8-10): target scores [3, 2, 1] -> mean 2 -> BDI = 2/10 = 0.2
    pairs = [
        (10, 10),
        (9, 9),
        (8, 8),
        (7, 7),
        (6, 6),
        (5, 5),
        (4, 4),
        (3, 3),
        (2, 2),
        (1, 1),
    ]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s, max_score=10.0)

    result = run_psychometric_analysis(q)
    assert result.top_group_difficulty_index == pytest.approx(0.9, abs=0.001)
    assert result.bottom_group_difficulty_index == pytest.approx(0.2, abs=0.001)
    assert result.difference_difficulty_index == pytest.approx(0.7, abs=0.001)


# ---------------------------------------------------------------------------
# Non-MCQ Item Total Correlation (SRS §5)
# ---------------------------------------------------------------------------


def test_non_mcq_item_total_correlation_positive_when_correlated():
    """When target scores and total scores are positively correlated,
    the Item-Total Correlation should be positive (close to 1 for
    perfect correlation).

    Setup: target_score = total_score / 10 * 10 (perfect correlation)
    """
    q = _make_question(qtype="FITB_TEXT", scoring_type="PARTIAL")
    assessment = Assessment.objects.create(title="A", status="published")
    # Perfectly correlated: target = total (both 1-10)
    pairs = [(i, i) for i in range(1, 11)]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s, max_score=10.0)

    result = run_psychometric_analysis(q)
    assert result.item_total_correlation is not None
    # Perfect correlation should give a value close to 1
    assert result.item_total_correlation > 0.9


def test_non_mcq_item_total_correlation_none_when_no_variance():
    """If all target scores are the same, SD-Target=0 -> correlation None."""
    q = _make_question(qtype="FITB_TEXT", scoring_type="PARTIAL")
    assessment = Assessment.objects.create(title="A", status="published")
    # All target=5, varying total
    pairs = [(5, 10), (5, 8), (5, 6), (5, 4)]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s, max_score=10.0)

    result = run_psychometric_analysis(q)
    assert result.item_total_correlation is None  # SD-Target = 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_results_persisted_on_question_model():
    """The computed indices are saved onto the Question model."""
    q = _make_question()
    assessment = Assessment.objects.create(title="A", status="published")
    pairs = [(1, 10), (1, 9), (0, 5), (0, 4)]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s)

    run_psychometric_analysis(q)
    q.refresh_from_db()
    assert q.item_difficulty_index is not None
    assert q.top_group_difficulty_index is not None
    assert q.bottom_group_difficulty_index is not None
    assert q.difference_difficulty_index is not None
    assert q.discrimination_index is not None  # MCQ
    assert q.item_total_correlation is None  # MCQ, not non-MCQ
    assert q.psychometric_analyzed_at is not None


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def test_date_filter_excludes_old_sessions():
    """date_from filter excludes sessions completed before the given date."""
    from datetime import timedelta

    from django.utils import timezone

    q = _make_question()
    assessment = Assessment.objects.create(title="A", status="published")
    # 4 candidates
    pairs = [(1, 10), (1, 9), (0, 5), (0, 4)]
    for i, (s, ts) in enumerate(pairs):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(assessment, c, total_score=ts)
        _make_attempt(session, q, score=s)
        # Make 2 sessions old, 2 sessions new
        if i < 2:
            session.completed_at = timezone.now() - timedelta(days=30)
        else:
            session.completed_at = timezone.now()
        session.save(update_fields=["completed_at"])

    # Filter: only recent sessions
    cutoff = timezone.now() - timedelta(days=7)
    result = run_psychometric_analysis(q, date_from=cutoff)
    assert result.n_candidates == 2  # only the 2 recent sessions


def test_assessment_filter_excludes_other_assessments():
    """assessment_id filter only counts sessions from that assessment."""
    q = _make_question()
    a1 = Assessment.objects.create(title="A1", status="published")
    a2 = Assessment.objects.create(title="A2", status="published")
    # 2 candidates on each assessment
    for i, a in enumerate([a1, a1, a2, a2]):
        c = _make_candidate(f"c{i}@test.com")
        session = _make_completed_session(a, c, total_score=5)
        _make_attempt(session, q, score=1 if i % 2 == 0 else 0)

    result = run_psychometric_analysis(q, assessment_id=a1.id)
    assert result.n_candidates == 2
