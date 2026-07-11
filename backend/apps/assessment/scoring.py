"""Scoring engine for the Assessment module.

Implements all 9 scoring modes per SRS 00_scoring_rules.json:
  - BINARY: 0 or 1 (exact match)
  - BINARY_FUZZY: 0 or 1 with fuzzy/percentage match (FITB)
  - PARTIAL: partial credit per correct item
  - NEGATIVE: correct = +1, wrong = -fraction
  - RANK: rank order scoring
  - RANK_RATE: rank score x rating score
  - RATING: rating value = score (forward/reverse)
  - FORCED_CHOICE: predefined score per option
  - FORCED_CHOICE_RATED: predefined score x rating

Each function takes the question, the candidate's raw_answer (JSON),
and returns (score, max_score).
"""

from typing import Any

from apps.question_bank.models import Question


def score_question(question: Question, raw_answer: dict[str, Any] | None) -> tuple[float, float]:
    """Score a single question based on its scoring_type.

    Returns (score, max_score).
    """
    if not raw_answer:
        return 0.0, _get_max_score(question)

    scorer = SCORERS.get(question.scoring_type)
    if not scorer:
        # Default to binary
        scorer = _score_binary

    return scorer(question, raw_answer)


def _get_max_score(question: Question) -> float:
    """Get the maximum possible score for a question."""
    st = question.scoring_type
    if st in ("BINARY", "BINARY_FUZZY"):
        return 1.0
    elif st == "PARTIAL":
        # Max = number of scoreable items.
        # For FITB multi-field: 1 per option (field).
        # For Match: 1 per pair = half the options (half A, half B).
        n_opts = question.options.count()
        has_match = question.options.filter(option_type__in=["MATCH_A", "MATCH_B"]).exists()
        if has_match:
            return float(n_opts / 2)  # pairs
        return float(n_opts)
    elif st == "NEGATIVE":
        return 1.0
    elif st == "RANK":
        # Rank scoring counts correct pairs (i<j in correct order).
        # Number of pairs = n*(n-1)/2.
        n = question.options.count()
        return float(n * (n - 1) / 2) if n > 0 else 1.0
    elif st == "RANK_RATE":
        n = question.options.count()
        max_rating = question.rating_scale_points or 5
        return float(n * max_rating)
    elif st == "RATING":
        return float(question.rating_scale_points or 5)
    elif st == "FORCED_CHOICE":
        opts = list(question.options.all())
        return float(max((o.predefined_score for o in opts), default=1.0))
    elif st == "FORCED_CHOICE_RATED":
        opts = list(question.options.all())
        max_predefined = max((o.predefined_score for o in opts), default=1.0)
        max_rating = question.rating_scale_points or 5
        return float(max_predefined * max_rating)
    return 1.0


# ---------------------------------------------------------------------------
# BINARY: 0 or 1 — exact match
# Used by: MCQ (1a-1h), FITB single (2a), Hotspot single (5a)
# ---------------------------------------------------------------------------


def _score_binary(question: Question, raw_answer: dict) -> tuple[float, float]:
    """Correct answer selected → 1, else 0."""
    max_score = 1.0
    selected_ids = raw_answer.get("selected_option_ids", [])
    if not selected_ids and "selected_option_id" in raw_answer:
        selected_ids = [raw_answer["selected_option_id"]]

    correct_options = list(question.options.filter(is_correct=True))
    if not correct_options:
        return 0.0, max_score

    correct_ids = [o.id for o in correct_options]
    # For single-answer: check if selected matches any correct
    if len(correct_options) == 1:
        score = 1.0 if set(selected_ids) == {correct_ids[0]} else 0.0
    else:
        # For multi-answer binary: all correct selected, none incorrect
        selected_set = set(selected_ids)
        correct_set = set(correct_ids)
        score = 1.0 if selected_set == correct_set else 0.0

    return score, max_score


# ---------------------------------------------------------------------------
# BINARY_FUZZY: 0 or 1 with fuzzy/percentage match
# Used by: FITB single (2a)
# ---------------------------------------------------------------------------


def _score_binary_fuzzy(question: Question, raw_answer: dict) -> tuple[float, float]:
    """FITB: match against list (Mode A) or percentage match (Mode B)."""
    max_score = 1.0
    candidate_text = raw_answer.get("text", "").strip()
    if not candidate_text:
        return 0.0, max_score

    if not question.case_sensitive:
        candidate_text = candidate_text.lower()

    # Get correct answers from the first option's correct_answers
    opt = question.options.first()
    if not opt:
        return 0.0, max_score

    correct_answers = [ca.answer_text for ca in opt.correct_answers.all()]
    if not question.case_sensitive:
        correct_answers = [c.lower() for c in correct_answers]

    if question.pct_match_threshold is not None:
        # Mode B: percentage match against single correct answer
        if not correct_answers:
            return 0.0, max_score
        correct = correct_answers[0]
        if len(correct) == 0:
            return 1.0 if len(candidate_text) == 0 else 0.0, max_score
        matches = sum(a == b for a, b in zip(candidate_text, correct, strict=False))
        pct = (matches / len(correct)) * 100
        score = 1.0 if pct >= question.pct_match_threshold else 0.0
    else:
        # Mode A: match any in list
        score = 1.0 if candidate_text in [c.strip() for c in correct_answers] else 0.0

    return score, max_score


# ---------------------------------------------------------------------------
# PARTIAL: partial credit per correct item
# Used by: FITB multi-field (2b), Match (3)
# ---------------------------------------------------------------------------


def _score_partial(question: Question, raw_answer: dict) -> tuple[float, float]:
    """Each correct item = +1, incorrect = 0. Total = sum of correct items.

    Supports two question types:
      - FITB multi-field (2b): raw_answer = {"answers": ["a", "b", ...]}
        Max score = number of fields (options).
      - Match-the-following (3): raw_answer = {"pairs": [{"a_id": 1, "b_id": 3}, ...]}
        Max score = number of pairs (half the options).
    """
    options = list(question.options.all().order_by("order"))
    if not options:
        return 0.0, 0.0

    # Detect Match-the-following by option_type
    has_match = any(o.option_type in ("MATCH_A", "MATCH_B") for o in options)
    max_score = float(len(options) / 2) if has_match else float(len(options))

    # For FITB multi-field: raw_answer = {"answers": ["ans1", "ans2", ...]}
    answers = raw_answer.get("answers", [])
    if answers:
        score = 0.0
        for i, opt in enumerate(options):
            if i < len(answers):
                candidate = answers[i].strip()
                if not question.case_sensitive:
                    candidate = candidate.lower()
                correct_list = (
                    [ca.answer_text.lower() for ca in opt.correct_answers.all()]
                    if not question.case_sensitive
                    else [ca.answer_text for ca in opt.correct_answers.all()]
                )
                if candidate in [c.strip() for c in correct_list]:
                    score += 1.0
        return score, max_score

    # For Match: raw_answer = {"pairs": [{"a_id": 1, "b_id": 3}, ...]}
    pairs = raw_answer.get("pairs", [])
    if pairs:
        match_a = {o.id: o.match_pair_id for o in options if o.option_type == "MATCH_A"}
        match_b = {o.id: o.match_pair_id for o in options if o.option_type == "MATCH_B"}
        score = 0.0
        for pair in pairs:
            a_id = pair.get("a_id")
            b_id = pair.get("b_id")
            if a_id in match_a and b_id in match_b and match_a[a_id] == match_b[b_id]:
                score += 1.0
        return score, max_score

    return 0.0, max_score


# ---------------------------------------------------------------------------
# NEGATIVE: correct = +1, wrong = -fraction
# Used by: Hotspot multi (5b), configurable for MCQ
# ---------------------------------------------------------------------------


def _score_negative(question: Question, raw_answer: dict) -> tuple[float, float]:
    """Correct = +1, wrong = -0.25 (configurable). Floor at 0."""
    max_score = 1.0
    negative_fraction = 0.25  # TODO: make configurable per question

    selected_ids = raw_answer.get("selected_option_ids", [])
    if not selected_ids and "selected_option_id" in raw_answer:
        selected_ids = [raw_answer["selected_option_id"]]

    correct_options = list(question.options.filter(is_correct=True))
    correct_ids = {o.id for o in correct_options}

    if not selected_ids:
        return 0.0, max_score

    selected_set = set(selected_ids)
    if selected_set <= correct_ids:
        # All selected are correct
        if selected_set == correct_ids:
            return 1.0, max_score
        return 0.5, max_score  # partial
    else:
        # Some wrong selections
        return max(0.0, -negative_fraction), max_score


# ---------------------------------------------------------------------------
# RANK: rank order scoring
# Used by: Rank Simple (6a)
# ---------------------------------------------------------------------------


def _score_rank(question: Question, raw_answer: dict) -> tuple[float, float]:
    """Score = number of items in correct relative order.

    Max score = n*(n-1)/2 (number of unique pairs).
    """
    options = list(question.options.all().order_by("order"))
    n = len(options)
    max_score = float(n * (n - 1) / 2) if n > 0 else 1.0

    # raw_answer = {"ranking": [3, 1, 4, 2]} — option IDs in rank order
    ranking = raw_answer.get("ranking", [])
    if not ranking or len(ranking) != n:
        return 0.0, max_score

    # The correct order is the option order as stored (order field)
    correct_order = [o.id for o in sorted(options, key=lambda x: x.order)]

    # Score = count of pairs in correct relative order
    score = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            # Check if ranking[i] comes before ranking[j] in correct_order
            pos_i = correct_order.index(ranking[i]) if ranking[i] in correct_order else -1
            pos_j = correct_order.index(ranking[j]) if ranking[j] in correct_order else -1
            if pos_i >= 0 and pos_j >= 0 and pos_i < pos_j:
                score += 1.0

    return score, max_score


# ---------------------------------------------------------------------------
# RANK_RATE: rank score x rating score
# Used by: Rank-then-Rate (6b)
# ---------------------------------------------------------------------------


def _score_rank_rate(question: Question, raw_answer: dict) -> tuple[float, float]:
    """Final score per option = rank_score x rating_score."""
    options = list(question.options.all().order_by("order"))
    n = len(options)
    max_rating = question.rating_scale_points or 5
    max_score = float(n * max_rating)

    # raw_answer = {"ranking": [3, 1, 4, 2], "ratings": {3: 5, 1: 3, 4: 1, 2: 4}}
    ranking = raw_answer.get("ranking", [])
    ratings = raw_answer.get("ratings", {})

    if not ranking or len(ranking) != n:
        return 0.0, max_score

    score = 0.0
    for rank_pos, opt_id in enumerate(ranking):
        rank_score = n - rank_pos  # Rank 1 → n, Rank 2 → n-1, etc.
        rating = ratings.get(str(opt_id), ratings.get(opt_id, 0))
        score += rank_score * float(rating)

    return score, max_score


# ---------------------------------------------------------------------------
# RATING: rating value = score (forward/reverse)
# Used by: Standard Rating Scale (7)
# ---------------------------------------------------------------------------


def _score_rating(question: Question, raw_answer: dict) -> tuple[float, float]:
    """Score = rating point selected. Forward: leftmost=highest. Reverse: rightmost=highest."""
    scale_points = question.rating_scale_points or 5
    max_score = float(scale_points)

    # raw_answer = {"rating": 4} — 1-indexed from left
    rating = raw_answer.get("rating", 0)
    if not rating:
        return 0.0, max_score

    if question.rating_direction == "FORWARD":
        # Forward: leftmost (1) = highest score (n), rightmost (n) = 1
        score = float(scale_points - rating + 1)
    else:
        # Reverse: leftmost (1) = 1, rightmost (n) = highest
        score = float(rating)

    return score, max_score


# ---------------------------------------------------------------------------
# FORCED_CHOICE: predefined score per option
# Used by: Forced-Choice Single Level (8a)
# ---------------------------------------------------------------------------


def _score_forced_choice(question: Question, raw_answer: dict) -> tuple[float, float]:
    """Score = selected option's predefined_score. Unselected = 0."""
    options = list(question.options.all())
    max_score = float(max((o.predefined_score for o in options), default=1.0))

    # raw_answer = {"selected_option_id": 2}
    selected_id = raw_answer.get("selected_option_id")
    if not selected_id:
        return 0.0, max_score

    for opt in options:
        if opt.id == selected_id:
            return float(opt.predefined_score), max_score

    return 0.0, max_score


# ---------------------------------------------------------------------------
# FORCED_CHOICE_RATED: predefined score x rating
# Used by: Forced-Choice Two-Level (8b)
# ---------------------------------------------------------------------------


def _score_forced_choice_rated(question: Question, raw_answer: dict) -> tuple[float, float]:
    """Score = predefined_score x rating. Unselected = 0."""
    options = list(question.options.all())
    max_rating = question.rating_scale_points or 5
    max_predefined = max((o.predefined_score for o in options), default=1.0)
    max_score = float(max_predefined * max_rating)

    # raw_answer = {"selected_option_id": 2, "rating": 4}
    selected_id = raw_answer.get("selected_option_id")
    rating = raw_answer.get("rating", 0)

    if not selected_id or not rating:
        return 0.0, max_score

    for opt in options:
        if opt.id == selected_id:
            return float(opt.predefined_score * rating), max_score

    return 0.0, max_score


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SCORERS = {
    "BINARY": _score_binary,
    "BINARY_FUZZY": _score_binary_fuzzy,
    "PARTIAL": _score_partial,
    "NEGATIVE": _score_negative,
    "RANK": _score_rank,
    "RANK_RATE": _score_rank_rate,
    "RATING": _score_rating,
    "FORCED_CHOICE": _score_forced_choice,
    "FORCED_CHOICE_RATED": _score_forced_choice_rated,
}


def calculate_session_scores(session):
    """Calculate all scores for a completed session.

    Called when a session is submitted. Iterates all QuestionAttempts,
    scores each one, then aggregates into SectionScores and session totals.
    """
    from .models import SectionScore

    attempts = session.question_attempts.select_related("question", "section").all()

    # Score each attempt
    section_scores: dict[int, dict] = {}  # section_id -> {raw, max}
    total_raw = 0.0
    total_max = 0.0

    for attempt in attempts:
        if attempt.status != "attempted" or not attempt.raw_answer:
            attempt.score = 0.0
            attempt.max_score = _get_max_score(attempt.question)
            attempt.save(update_fields=["score", "max_score"])
            continue

        score, max_score = score_question(attempt.question, attempt.raw_answer)
        attempt.score = score
        attempt.max_score = max_score
        attempt.save(update_fields=["score", "max_score"])

        total_raw += score
        total_max += max_score

        # Aggregate by section
        sid = attempt.section_id
        if sid:
            if sid not in section_scores:
                section_scores[sid] = {"raw": 0.0, "max": 0.0}
            section_scores[sid]["raw"] += score
            section_scores[sid]["max"] += max_score

    # Create/update SectionScore records
    for sid, scores in section_scores.items():
        SectionScore.objects.update_or_create(
            session=session,
            section_id=sid,
            defaults={
                "raw_score": scores["raw"],
                "max_score": scores["max"],
            },
        )

    # Update session totals
    session.total_score = total_raw
    session.max_score = total_max
    session.percentage = round((total_raw / total_max) * 100, 2) if total_max > 0 else 0
    session.save(update_fields=["total_score", "max_score", "percentage"])

    # Increment exposure count for each question used
    for attempt in attempts:
        question = attempt.question
        question.exposure_count += 1
        # Auto-deactivate if exposure limit reached
        if question.exposure_limit and question.exposure_count >= question.exposure_limit:
            question.is_active = False
        question.save(update_fields=["exposure_count", "is_active"])

    return session
