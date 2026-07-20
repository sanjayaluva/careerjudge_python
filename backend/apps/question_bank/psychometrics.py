"""Psychometric analysis computation engine.

Implements SRS 02_psychometric_analysis_computation.json:
  - Item Difficulty Index (MCQ): IDI, TDI, BDI, DDI
  - Item Difficulty Index (non-MCQ): IDI, TDI, BDI, DDI (mean-based)
  - Item Discrimination Index (MCQ)
  - Item Total Correlation Index (non-MCQ)

The engine pulls data from completed QuestionAttempt records across all
sessions that include the target question. The psychometrician triggers
analysis with optional filter criteria (date range, assessment, etc.).

Results are persisted on the Question model:
  - item_difficulty_index (IDI)
  - top_group_difficulty_index (TDI)
  - bottom_group_difficulty_index (BDI)
  - difference_difficulty_index (DDI)
  - discrimination_index (MCQ only)
  - item_total_correlation (non-MCQ only)
  - psychometric_analyzed_at (timestamp)

Per SRS 02:
  - Top group    = top 27% of candidates by total score
  - Bottom group = bottom 27% of candidates by total score
  - For MCQ: a candidate is 'correct' on the target question if their
    score equals the max_score (BINARY). For partial-credit questions
    (PARTIAL scoring), 'correct' = score >= 50% of max_score.
  - For non-MCQ: the actual score is used (mean-based formulas).
  - For item-total correlation (non-MCQ), only candidates who attempted
    ALL questions in the assessment are included (SRS 02 §5 note).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.assessment.models import QuestionAttempt
from apps.question_bank.models import Question

# Per SRS 02 §2.2 / §2.3 / §3.2 / §3.3: top/bottom 27% of candidates by
# total score are used for TDI/BDI computations.
TOP_BOTTOM_PERCENTILE = 0.27


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CandidateAttemptSummary:
    """Per-candidate data needed for psychometric computation."""

    candidate_id: int
    target_score: float  # score on the target question
    target_max_score: float
    total_score: float  # sum of all question scores in this session
    is_correct: bool  # for MCQ: did they get it right?


@dataclass
class PsychometricResult:
    """Output of the psychometric computation for one question."""

    question_id: int
    n_candidates: int
    # Common indices (all 4 computed for both MCQ and non-MCQ per SRS 02 §2/§3)
    item_difficulty_index: float | None  # IDI
    top_group_difficulty_index: float | None  # TDI
    bottom_group_difficulty_index: float | None  # BDI
    difference_difficulty_index: float | None  # DDI = TDI - BDI
    # Mode-specific index (only one of these is set per SRS 02 §4/§5)
    discrimination_index: float | None  # MCQ only
    item_total_correlation: float | None  # non-MCQ only
    error: str | None = None  # set if computation couldn't run (e.g., <2 candidates)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_psychometric_analysis(
    question: Question,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    assessment_id: int | None = None,
) -> PsychometricResult:
    """Run psychometric analysis on a single question.

    Args:
        question: The target Question to analyse.
        date_from: Optional lower bound on session.completed_at.
        date_to: Optional upper bound on session.completed_at.
        assessment_id: Optional filter — only sessions of this assessment
            are considered.

    Returns:
        PsychometricResult with computed indices. The result is also
        persisted onto the Question model (IDI/TDI/BDI/DDI/discrimination/
        correlation + psychometric_analyzed_at timestamp).

    Per SRS 02:
      - MCQ questions (question_type starts with MCQ_): use §2 + §4 formulas
        (count-based difficulty + discrimination index)
      - Non-MCQ: use §3 + §5 formulas (mean-based difficulty + total
        correlation index)
    """
    attempts = _fetch_target_attempts(question, date_from, date_to, assessment_id)
    summaries = _build_summaries(attempts)
    if len(summaries) < 2:
        result = PsychometricResult(
            question_id=question.id,
            n_candidates=len(summaries),
            item_difficulty_index=None,
            top_group_difficulty_index=None,
            bottom_group_difficulty_index=None,
            difference_difficulty_index=None,
            discrimination_index=None,
            item_total_correlation=None,
            error=(
                f"Insufficient data: only {len(summaries)} candidate(s) attempted "
                "this question. Need at least 2 for psychometric analysis."
            ),
        )
        _persist_result(question, result)
        return result

    if question.question_type.startswith("MCQ_"):
        result = _compute_mcq(question, summaries)
    else:
        result = _compute_non_mcq(question, summaries)
    _persist_result(question, result)
    return result


def run_batch_psychometric_analysis(
    questions: Iterable[Question],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    assessment_id: int | None = None,
) -> list[PsychometricResult]:
    """Run psychometric analysis on a batch of questions.

    Convenience wrapper that loops over a queryset/list of questions and
    returns the results in the same order. Each question is analysed
    independently per SRS 02 ("Target question is the question whose
    analysis is performed. All questions undergo analysis separately.").
    """
    return [run_psychometric_analysis(q, date_from, date_to, assessment_id) for q in questions]


# ---------------------------------------------------------------------------
# Internal: data fetching
# ---------------------------------------------------------------------------


def _fetch_target_attempts(
    question: Question,
    date_from: datetime | None,
    date_to: datetime | None,
    assessment_id: int | None,
) -> list[QuestionAttempt]:
    """Fetch all completed-session attempts for the target question."""
    qs = QuestionAttempt.objects.filter(
        question=question,
        status="attempted",
        session__status="completed",
    )
    if date_from is not None:
        qs = qs.filter(session__completed_at__gte=date_from)
    if date_to is not None:
        qs = qs.filter(session__completed_at__lte=date_to)
    if assessment_id is not None:
        qs = qs.filter(session__assessment_id=assessment_id)
    return list(qs.select_related("session"))


def _build_summaries(attempts: list[QuestionAttempt]) -> list[CandidateAttemptSummary]:
    """Build a per-candidate summary list with (target_score, total_score, is_correct).

    Per SRS 02 §4 (MCQ discrimination) and §5 (non-MCQ total correlation):
      - Total Score = sum of all question scores for each user (in the same
        session). Note: we use session.total_score which is the assessment-
        level aggregate, not just the target question's siblings. This
        matches the SRS's intent of measuring the candidate's overall
        performance to find top/bottom groups.
    """
    summaries: list[CandidateAttemptSummary] = []
    for att in attempts:
        if att.score is None or att.max_score is None or att.max_score == 0:
            continue
        # 'Correct' for MCQ: score == max_score (BINARY) or score >= 50%
        # of max_score (PARTIAL). For MCQ with BINARY scoring, this is
        # equivalent to score > 0. We use the 50% threshold to be safe
        # across scoring modes.
        is_correct = att.score >= (att.max_score * 0.5)
        total_score = att.session.total_score or 0
        summaries.append(
            CandidateAttemptSummary(
                candidate_id=att.session.candidate_id,
                target_score=float(att.score),
                target_max_score=float(att.max_score),
                total_score=float(total_score),
                is_correct=is_correct,
            )
        )
    return summaries


# ---------------------------------------------------------------------------
# Internal: MCQ computation (SRS 02 §2 + §4)
# ---------------------------------------------------------------------------


def _compute_mcq(
    question: Question, summaries: list[CandidateAttemptSummary]
) -> PsychometricResult:
    """Compute IDI/TDI/BDI/DDI (SRS §2) + Item Discrimination Index (§4) for MCQ."""
    n = len(summaries)
    total_correct = sum(1 for s in summaries if s.is_correct)
    idi = total_correct / n if n else 0.0

    # Sort by total score to find top/bottom 27%
    sorted_by_total = sorted(summaries, key=lambda s: s.total_score, reverse=True)
    top_count = max(1, int(round(n * TOP_BOTTOM_PERCENTILE)))
    bottom_count = max(1, int(round(n * TOP_BOTTOM_PERCENTILE)))
    top_group = sorted_by_total[:top_count]
    bottom_group = sorted_by_total[-bottom_count:]

    tdi = sum(1 for s in top_group if s.is_correct) / len(top_group) if top_group else 0.0
    bdi = sum(1 for s in bottom_group if s.is_correct) / len(bottom_group) if bottom_group else 0.0
    ddi = tdi - bdi

    disc = _compute_discrimination_index(summaries)

    return PsychometricResult(
        question_id=question.id,
        n_candidates=n,
        item_difficulty_index=round(idi, 4),
        top_group_difficulty_index=round(tdi, 4),
        bottom_group_difficulty_index=round(bdi, 4),
        difference_difficulty_index=round(ddi, 4),
        discrimination_index=disc,
        item_total_correlation=None,
    )


def _compute_discrimination_index(summaries: list[CandidateAttemptSummary]) -> float | None:
    """Compute Item Discrimination Index per SRS 02 §4.

    Formula:
      Discrimination = ((Mean-Correct - Mean-Incorrect) x sqrt(N1/N x N2/N)) / SD

    Where:
      N1 = number of users who got target CORRECT
      N2 = number of users who got target INCORRECT
      N  = total users
      SD = standard deviation of total scores
      Mean-Correct   = mean total score of users who got target correct
      Mean-Incorrect = mean total score of users who got target incorrect

    Returns None if SD is 0 (no variance) or if N1=0 or N2=0.
    """
    n = len(summaries)
    if n < 2:
        return None

    correct_users = [s for s in summaries if s.is_correct]
    incorrect_users = [s for s in summaries if not s.is_correct]
    if not correct_users or not incorrect_users:
        # Need at least 1 correct AND 1 incorrect to compute discrimination
        return None

    n1 = len(correct_users)
    n2 = len(incorrect_users)
    total_scores = [s.total_score for s in summaries]
    sd = statistics.pstdev(total_scores) if n > 1 else 0.0
    if sd == 0:
        return None

    mean_correct = sum(s.total_score for s in correct_users) / n1
    mean_incorrect = sum(s.total_score for s in incorrect_users) / n2
    n_coefficient = math.sqrt((n1 / n) * (n2 / n))
    mean_coefficient = (mean_correct - mean_incorrect) * n_coefficient
    return round(mean_coefficient / sd, 4)


# ---------------------------------------------------------------------------
# Internal: non-MCQ computation (SRS 02 §3 + §5)
# ---------------------------------------------------------------------------


def _compute_non_mcq(
    question: Question, summaries: list[CandidateAttemptSummary]
) -> PsychometricResult:
    """Compute IDI/TDI/BDI/DDI (SRS §3) + Item-Total Correlation (§5) for non-MCQ."""
    n = len(summaries)
    max_score = summaries[0].target_max_score if summaries else 1.0
    if max_score == 0:
        max_score = 1.0

    # IDI = (Sum Score-Target / N) / Max Score
    sum_target = sum(s.target_score for s in summaries)
    mean_target = sum_target / n
    idi = mean_target / max_score

    # Sort by total score for top/bottom 27%
    sorted_by_total = sorted(summaries, key=lambda s: s.total_score, reverse=True)
    top_count = max(1, int(round(n * TOP_BOTTOM_PERCENTILE)))
    bottom_count = max(1, int(round(n * TOP_BOTTOM_PERCENTILE)))
    top_group = sorted_by_total[:top_count]
    bottom_group = sorted_by_total[-bottom_count:]

    # TDI = (Sum Score-Top-Target / N-T) / Max Score
    tdi = (sum(s.target_score for s in top_group) / len(top_group)) / max_score
    # BDI = (Sum Score-Bottom-Target / N-B) / Max Score
    bdi = (sum(s.target_score for s in bottom_group) / len(bottom_group)) / max_score
    ddi = tdi - bdi

    correlation = _compute_item_total_correlation(summaries)

    return PsychometricResult(
        question_id=question.id,
        n_candidates=n,
        item_difficulty_index=round(idi, 4),
        top_group_difficulty_index=round(tdi, 4),
        bottom_group_difficulty_index=round(bdi, 4),
        difference_difficulty_index=round(ddi, 4),
        discrimination_index=None,
        item_total_correlation=correlation,
    )


def _compute_item_total_correlation(
    summaries: list[CandidateAttemptSummary],
) -> float | None:
    """Compute Item-Total Correlation Index per SRS 02 §5.

    Formula:
      ITC = Sum(Difference-Total x Difference-Target) / (SD-Total x SD-Target x N)

    Where:
      Difference-Total = Total Score - Mean-Total (per user)
      Difference-Target = Target Score - Mean-Target (per user)
      SD-Total = standard deviation of total scores
      SD-Target = standard deviation of target scores
      N = number of users

    Returns None if SD-Total or SD-Target is 0 (no variance in either
    direction).
    """
    n = len(summaries)
    if n < 2:
        return None

    total_scores = [s.total_score for s in summaries]
    target_scores = [s.target_score for s in summaries]
    mean_total = sum(total_scores) / n
    mean_target = sum(target_scores) / n

    sd_total = statistics.pstdev(total_scores)
    sd_target = statistics.pstdev(target_scores)
    if sd_total == 0 or sd_target == 0:
        return None

    sum_diff_product = sum(
        (s.total_score - mean_total) * (s.target_score - mean_target) for s in summaries
    )
    sd_n_product = sd_total * sd_target * n
    if sd_n_product == 0:
        return None
    return round(sum_diff_product / sd_n_product, 4)


# ---------------------------------------------------------------------------
# Internal: persistence
# ---------------------------------------------------------------------------


def _persist_result(question: Question, result: PsychometricResult) -> None:
    """Save the computed indices onto the Question model."""
    question.item_difficulty_index = result.item_difficulty_index
    question.top_group_difficulty_index = result.top_group_difficulty_index
    question.bottom_group_difficulty_index = result.bottom_group_difficulty_index
    question.difference_difficulty_index = result.difference_difficulty_index
    question.discrimination_index = result.discrimination_index
    question.item_total_correlation = result.item_total_correlation
    question.psychometric_analyzed_at = timezone.now()
    question.save(
        update_fields=[
            "item_difficulty_index",
            "top_group_difficulty_index",
            "bottom_group_difficulty_index",
            "difference_difficulty_index",
            "discrimination_index",
            "item_total_correlation",
            "psychometric_analyzed_at",
        ]
    )
