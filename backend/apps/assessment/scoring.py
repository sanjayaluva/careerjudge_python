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


def score_question(
    question: Question,
    raw_answer: dict[str, Any] | None,
    sub_question_index: int = 0,
) -> tuple[float, float]:
    """Score a single question based on its scoring_type.

    Returns (score, max_score).

    ``sub_question_index`` filters the question's options/hotspot areas to
    only those belonging to the given sub-question (for multi-sub-question
    pooled types 1c-1h). Default 0 = single question.
    """
    if not raw_answer:
        return 0.0, _get_max_score(question, sub_question_index)

    # Hotspot questions need special handling — they use clicks, not options.
    # Route them to the hotspot scorer regardless of their scoring_type.
    if question.question_type in ("HOTSPOT_SINGLE", "HOTSPOT_MULTI"):
        return _score_hotspot(question, raw_answer, sub_question_index)

    # Grid questions use their own scoring: correct = +1, incorrect = -1, min 0
    if question.question_type == "GRID_LIST_SELECTION":
        return _score_grid(question, raw_answer, sub_question_index)

    # FITB single (2a) is text-matched against a list, not option-id matched.
    # Route it to the fuzzy/list scorer regardless of a stale scoring_type —
    # the model default is "BINARY", which would send a text answer through the
    # option-id matcher and always score 0 (QT-1; 00_scoring_rules.json 2a =
    # BINARY_FUZZY, Mode A). Mirrors the hotspot/grid special-casing above.
    if question.question_type == "FITB_SINGLE":
        return _score_binary_fuzzy(question, raw_answer, sub_question_index)

    scorer = SCORERS.get(question.scoring_type)
    if not scorer:
        # Default to binary
        scorer = _score_binary

    return scorer(question, raw_answer, sub_question_index)


def score_question_by_section(
    question: Question,
    raw_answer: dict[str, Any] | None,
    sub_question_index: int = 0,
) -> dict[str, tuple[float, float]] | None:
    """Return per-section-tag scores for psychometric question types.

    For RANK / RANK_RATE / FORCED_CHOICE / FORCED_CHOICE_RATED, returns a
    dict mapping each option's ``section_tag`` → ``(raw_score, max_score)``
    so the caller (``calculate_session_scores``) can route each option's
    score into the AssessmentSection that the tag resolves to.

    Returns ``None`` for non-psychometric types (caller should use the
    normal single-section aggregation path via ``score_question``).

    Options with an empty ``section_tag`` are grouped under the empty
    string "" key (caller decides how to handle — typically falls back to
    the question's own section).
    """
    if question.scoring_type not in ("RANK", "RANK_RATE", "FORCED_CHOICE", "FORCED_CHOICE_RATED"):
        return None

    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    options = list(opts_qs.all().order_by("order"))
    n = len(options)

    # Seed every option's tag with a (0, 0) entry so tags with no score
    # contribution still appear (max_score tracking).
    result: dict[str, list[float]] = {}  # tag -> [raw, max]
    for opt in options:
        result.setdefault(opt.section_tag or "", [0.0, 0.0])

    if question.scoring_type == "RANK":
        # Each option ranked r -> score (N - r + 1). Each option's achievable
        # max is N (if it were ranked 1). Assign that max to the option's OWN
        # tag (NOT every tag) so the per-section max sum equals N.
        ranking = (raw_answer or {}).get("ranking", [])
        max_per_opt = float(n) if n > 0 else 1.0
        for opt in options:
            result[opt.section_tag or ""][1] += max_per_opt
        if ranking and len(ranking) == n:
            for rank_pos, opt_id in enumerate(ranking):
                opt = next((o for o in options if o.id == opt_id), None)
                if opt is None:
                    continue
                result[opt.section_tag or ""][0] += float(n - rank_pos)
        return {t: (v[0], v[1]) for t, v in result.items()}

    if question.scoring_type == "RANK_RATE":
        # score per option = rank_score * rating; max per option = N * max_rating.
        # Assign each option's max to its own tag.
        max_rating = question.rating_scale_points or 5
        max_per_opt = float(n * max_rating)
        for opt in options:
            result[opt.section_tag or ""][1] += max_per_opt
        ranking = (raw_answer or {}).get("ranking", [])
        ratings = (raw_answer or {}).get("ratings", {})
        if ranking and len(ranking) == n:
            for rank_pos, opt_id in enumerate(ranking):
                opt = next((o for o in options if o.id == opt_id), None)
                if opt is None:
                    continue
                rating = ratings.get(str(opt_id), ratings.get(opt_id, 0))
                result[opt.section_tag or ""][0] += float(n - rank_pos) * float(rating)
        return {t: (v[0], v[1]) for t, v in result.items()}

    # FORCED_CHOICE / FORCED_CHOICE_RATED — exactly 2 options per pair.
    # Selected → selection_score (* rating if rated); non-selected → non_selection_score.
    selected_id = (raw_answer or {}).get("selected_option_id")
    rating = (raw_answer or {}).get("rating", 0)
    max_rating = question.rating_scale_points or 5

    for opt in options:
        tag = opt.section_tag or ""
        is_selected = opt.id == selected_id
        if question.scoring_type == "FORCED_CHOICE":
            raw = float(opt.selection_score) if is_selected else float(opt.non_selection_score)
            mx = float(max(opt.selection_score, opt.non_selection_score))
        else:  # FORCED_CHOICE_RATED
            if is_selected and rating:
                raw = float(opt.selection_score) * float(rating)
                mx = float(opt.selection_score) * float(max_rating)
            elif is_selected:
                raw = 0.0  # rating required for the selected option
                mx = float(opt.selection_score) * float(max_rating)
            else:
                raw = float(opt.non_selection_score)
                mx = max(
                    float(opt.selection_score) * float(max_rating), float(opt.non_selection_score)
                )
        result[tag][0] += raw
        result[tag][1] += mx
    return {t: (v[0], v[1]) for t, v in result.items()}


def _get_max_score(question: Question, sub_question_index: int = 0) -> float:
    """Get the maximum possible score for a question.

    When ``sub_question_index`` is provided, only counts options belonging
    to that sub-question.
    """
    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    st = question.scoring_type
    if st in ("BINARY", "BINARY_FUZZY"):
        return 1.0
    elif st == "PARTIAL":
        # Max = number of scoreable items.
        # For FITB multi-field: 1 per option (field).
        # For Match: 1 per pair = half the options (half A, half B).
        n_match_a = opts_qs.filter(option_type="MATCH_A").count()
        if n_match_a:
            return float(n_match_a)  # pairs; MATCH_DUMMY distractors excluded
        return float(opts_qs.count())
    elif st == "NEGATIVE":
        return 1.0
    elif st == "RANK":
        # A complete ranking always sums to N(N+1)/2 (rank 1 -> N ... rank
        # N -> 1), so that is the true achievable total for the question.
        n = opts_qs.count()
        return float(n * (n + 1) / 2) if n > 0 else 1.0
    elif st == "RANK_RATE":
        n = opts_qs.count()
        max_rating = question.rating_scale_points or 5
        # Complete ranking sums rank-values to N(N+1)/2; each option can
        # also earn the max rating, so the true achievable total is that
        # sum times the max rating.
        return float(max_rating * n * (n + 1) / 2)
    elif st == "RATING":
        return float(question.rating_scale_points or 5)
    elif st == "FORCED_CHOICE":
        opts = list(opts_qs.all())
        # The pair pays selection (one option) + non-selection (the other):
        # max achievable = max(selection) + max(non-selection).
        max_sel = max((o.selection_score for o in opts), default=1.0)
        max_non = max((o.non_selection_score for o in opts), default=0.0)
        return float(max_sel + max_non)
    elif st == "FORCED_CHOICE_RATED":
        opts = list(opts_qs.all())
        max_rating = question.rating_scale_points or 5
        # Selected earns selection_score * rating; non-selected earns its
        # non_selection_score: max = max(sel*max_rating) + max(non_selection).
        best_sel = max((o.selection_score * max_rating for o in opts), default=1.0)
        best_non = max((o.non_selection_score for o in opts), default=0.0)
        return float(best_sel + best_non)
    return 1.0


# ---------------------------------------------------------------------------
# BINARY: 0 or 1 — exact match
# Used by: MCQ (1a-1h), FITB single (2a), Hotspot single (5a)
# ---------------------------------------------------------------------------


def _score_binary(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Score MCQ questions.

    Single-answer (1 correct option): correct → 1, incorrect → 0.
    Multi-answer (2+ correct options): each correct selected = +1, each
    incorrect selected = -1, minimum score = 0.

    Per SRS feedback report: 'each correct answer option selected by the
    test taker should receive a score of 1 and each incorrect answer
    option selected a score of -1. If the number of wrong answers
    selected is more than the number of correct answers selected, then
    the score is fixed at zero. The total score cannot be a negative
    value.'

    Max score = number of correct options (so multi-answer questions
    can score higher than 1).

    ``sub_question_index`` filters to only this sub-question's options
    (for multi-sub-question pooled types 1c-1h).
    """
    selected_ids = raw_answer.get("selected_option_ids", [])
    if not selected_ids and "selected_option_id" in raw_answer:
        selected_ids = [raw_answer["selected_option_id"]]

    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    correct_options = list(opts_qs.filter(is_correct=True))
    if not correct_options:
        return 0.0, 1.0

    correct_ids = {o.id for o in correct_options}
    selected_set = set(selected_ids)

    # Single-answer: simple match
    if len(correct_options) == 1:
        score = 1.0 if selected_set == correct_ids else 0.0
        return score, 1.0

    # Multi-answer: +1 per correct selected, -1 per incorrect selected, min 0
    correct_selected = selected_set & correct_ids
    incorrect_selected = selected_set - correct_ids
    raw_score = len(correct_selected) - len(incorrect_selected)
    score = max(0.0, float(raw_score))
    max_score = float(len(correct_options))

    return score, max_score


# ---------------------------------------------------------------------------
# BINARY_FUZZY: 0 or 1 with fuzzy/percentage match
# Used by: FITB single (2a)
# ---------------------------------------------------------------------------


def _score_binary_fuzzy(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """FITB: match against list (Mode A) or percentage match (Mode B)."""
    max_score = 1.0
    candidate_text = raw_answer.get("text", "").strip()
    if not candidate_text:
        # The player submits FITB answers in the unified list format.
        answers_list = raw_answer.get("answers", [])
        candidate_text = (answers_list[0] if answers_list else "").strip()
    if not candidate_text:
        return 0.0, max_score

    if not question.case_sensitive:
        candidate_text = candidate_text.lower()

    # Get correct answers from the first option's correct_answers
    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    opt = opts_qs.first()
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


def _score_partial(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Each correct item = +1, incorrect = 0. Total = sum of correct items.

    Supports two question types:
      - FITB multi-field (2b): raw_answer = {"answers": ["a", "b", ...]}
        Max score = number of fields (options).
      - Match-the-following (3): raw_answer = {"pairs": [{"a_id": 1, "b_id": 3}, ...]}
        Max score = number of pairs (half the options).

    ``sub_question_index`` filters to only this sub-question's options
    (for multi-sub-question pooled types 1c-1h).
    """
    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    options = list(opts_qs.all().order_by("order"))
    if not options:
        return 0.0, 0.0

    # Detect Match-the-following by option_type. Scoreable pairs = the
    # number of Group-A items; Group-B distractors (MATCH_DUMMY) are NOT
    # pairs and must not inflate the max (retest: 0.0/7.5 -> must be 6/6).
    n_match_a = sum(1 for o in options if o.option_type == "MATCH_A")
    max_score = float(n_match_a) if n_match_a else float(len(options))

    # For FITB multi-field: raw_answer = {"answers": ["ans1", "ans2", ...]}
    answers = raw_answer.get("answers", [])
    if answers:
        # For FITB Flash (image/word) types: candidate can enter answers in
        # ANY order. Each correctly entered answer gets +1 (SRS feedback §11).
        # Match each candidate answer against the UNION of all options'
        # correct_answers, with each correct answer counted at most once.
        is_flash_fitb = question.question_type in (
            "FITB_IMAGE_FLASH_MULTI",
            "FITB_WORD_FLASH_MULTI",
        )
        if is_flash_fitb:
            # Build the set of all correct answers across all options
            all_correct = set()
            for opt in options:
                for ca in opt.correct_answers.all():
                    val = ca.answer_text.strip()
                    if not question.case_sensitive:
                        val = val.lower()
                    all_correct.add(val)
            max_score = float(len(all_correct))
            matched_correct = set()
            score = 0.0
            for ans in answers:
                candidate = (ans or "").strip()
                if not candidate:
                    continue
                if not question.case_sensitive:
                    candidate = candidate.lower()
                if candidate in all_correct and candidate not in matched_correct:
                    score += 1.0
                    matched_correct.add(candidate)
            return score, max_score

        # Standard FITB multi-field: positional match (answer[i] ↔ option[i])
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


def _score_negative(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Correct = +1, wrong = -0.25 (configurable). Floor at 0."""
    max_score = 1.0
    negative_fraction = 0.25  # TODO: make configurable per question

    selected_ids = raw_answer.get("selected_option_ids", [])
    if not selected_ids and "selected_option_id" in raw_answer:
        selected_ids = [raw_answer["selected_option_id"]]

    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    correct_options = list(opts_qs.filter(is_correct=True))
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


def _score_rank(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Rank scoring (SRS 00_scoring_rules.json §RANK + Report 2 §1).

    Each option assigned rank ``r`` (1 = highest) receives a score of
    ``N - r + 1``. The option's score is posted to its tagged section
    (handled in ``calculate_session_scores`` via ``score_question_by_section``).

    Returns ``(total_score, total_max_score)`` where total = sum of all
    option scores (= N if all options are ranked) and total max = N.

    raw_answer = {"ranking": [3, 1, 4, 2]} — option IDs in rank order
    (first element = rank 1).
    """
    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    options = list(opts_qs.all().order_by("order"))
    n = len(options)
    max_score = float(n * (n + 1) / 2) if n > 0 else 1.0

    ranking = raw_answer.get("ranking", [])
    if not ranking or len(ranking) != n:
        return 0.0, max_score

    # rank_pos is 0-indexed: ranking[0] is rank 1 → score N, ranking[1] is
    # rank 2 → score N-1, … ranking[n-1] is rank N → score 1.
    score = 0.0
    for rank_pos, _opt_id in enumerate(ranking):
        score += float(n - rank_pos)
    return score, max_score


# ---------------------------------------------------------------------------
# RANK_RATE: rank score x rating score
# Used by: Rank-then-Rate (6b)
# ---------------------------------------------------------------------------


def _score_rank_rate(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Rank-then-rate scoring (SRS §RANK_RATE + Report 2 §2).

    Per option: score = rank_score * rating_score, where
    rank_score = (N - rank + 1). Each option's score is posted to its tagged
    section. Total = sum across options.

    raw_answer = {"ranking": [3, 1, 4, 2], "ratings": {"3": 5, "1": 3, ...}}
    """
    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    options = list(opts_qs.all().order_by("order"))
    n = len(options)
    max_rating = question.rating_scale_points or 5
    max_score = float(max_rating * n * (n + 1) / 2)

    ranking = raw_answer.get("ranking", [])
    ratings = raw_answer.get("ratings", {})

    if not ranking or len(ranking) != n:
        return 0.0, max_score

    score = 0.0
    for rank_pos, opt_id in enumerate(ranking):
        rank_score = n - rank_pos  # Rank 1 → n, Rank n → 1
        rating = ratings.get(str(opt_id), ratings.get(opt_id, 0))
        score += rank_score * float(rating)
    return score, max_score


# ---------------------------------------------------------------------------
# RATING: rating value = score (forward/reverse)
# Used by: Standard Rating Scale (7)
# ---------------------------------------------------------------------------


def _score_rating(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
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


def _score_forced_choice(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Forced-choice scoring (Report 2 §3 — selection vs non-selection).

    Each question has exactly 2 options, each tagged to its OWN section.
    The SELECTED option earns its ``selection_score``; the NON-selected
    option earns its ``non_selection_score``. Both scores are posted (to
    different sections) via ``score_question_by_section``.

    Total = selection_score (of selected) + non_selection_score (of the other).
    Total max = max(selection_score, non_selection_score) across the pair
    (the candidate can earn at most the larger of the two for the section
    that gets it). See ``_get_max_score``.

    raw_answer = {"selected_option_id": 2}
    """
    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    options = list(opts_qs.all())
    max_sel = max((o.selection_score for o in options), default=1.0)
    max_non_sel = max((o.non_selection_score for o in options), default=0.0)
    max_score = float(max_sel + max_non_sel)

    selected_id = raw_answer.get("selected_option_id")
    if not selected_id:
        # No answer → both options score 0
        return 0.0, max_score

    total = 0.0
    for opt in options:
        if opt.id == selected_id:
            total += float(opt.selection_score)
        else:
            total += float(opt.non_selection_score)
    return total, max_score


# ---------------------------------------------------------------------------
# FORCED_CHOICE_RATED: predefined score x rating
# Used by: Forced-Choice Two-Level (8b)
# ---------------------------------------------------------------------------


def _score_forced_choice_rated(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Forced-choice two-level scoring (Report 2 §4).

    The SELECTED option earns ``selection_score * rating`` (rating only
    applies to the selected option). The NON-selected option earns its
    ``non_selection_score``. Both posted to their own sections.

    raw_answer = {"selected_option_id": 2, "rating": 4}
    """
    opts_qs = question.options.filter(sub_question_index=sub_question_index)
    options = list(opts_qs.all())
    max_rating = question.rating_scale_points or 5
    best_sel = max((o.selection_score * max_rating for o in options), default=1.0)
    best_non = max((o.non_selection_score for o in options), default=0.0)
    max_score = float(best_sel + best_non)

    selected_id = raw_answer.get("selected_option_id")
    rating = raw_answer.get("rating", 0)

    if not selected_id:
        return 0.0, max_score

    total = 0.0
    for opt in options:
        if opt.id == selected_id:
            if rating:
                total += float(opt.selection_score) * float(rating)
            # No rating → selected option scores 0 (rating is required)
        else:
            total += float(opt.non_selection_score)
    return total, max_score


# ---------------------------------------------------------------------------
# HOTSPOT: click-based scoring for image hotspot questions
# Used by: Hotspot Single (5a) and Hotspot Multi (5b)
# ---------------------------------------------------------------------------


def _score_hotspot(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Score hotspot questions based on candidate clicks.

    For HOTSPOT_SINGLE (5a, BINARY scoring):
      - If any click falls within a correct hotspot area → 1.0
      - Otherwise → 0.0

    For HOTSPOT_MULTI (5b, NEGATIVE scoring):
      - Each correct click → +1/n (where n = number of correct areas)
      - Each wrong click → -0.25/n
      - Floor at 0

    The candidate's answer format is:
      {"clicks": [{"x": 142, "y": 159}, ...]}

    ``sub_question_index`` filters to only this sub-question's hotspot areas.
    """
    max_score = 1.0
    clicks = raw_answer.get("clicks", [])
    if not clicks:
        return 0.0, max_score

    # Get all hotspot areas for this question (filtered by sub-question)
    areas_qs = question.hotspot_areas
    if sub_question_index:
        areas_qs = areas_qs.filter(sub_question_index=sub_question_index)
    areas = list(areas_qs.all())
    if not areas:
        return 0.0, max_score

    correct_areas = [a for a in areas if a.is_correct]
    if not correct_areas:
        # No correct areas defined → can't score
        return 0.0, max_score

    is_multi = question.question_type == "HOTSPOT_MULTI"

    if not is_multi:
        # Single answer (5a): correct if ANY click is within a correct area
        for click in clicks:
            cx = click.get("x", 0)
            cy = click.get("y", 0)
            for area in correct_areas:
                if area.contains_point(cx, cy):
                    return 1.0, max_score
        return 0.0, max_score
    else:
        # Multi answer (5b): each correct click = +1, each wrong click = -1, min 0
        # Per SRS feedback: 'Each correct selection should be given a score
        # of 1. Each incorrect selection should receive a negative score
        # of 1, but minimum score is zero, not a negative value.'
        correct_clicks = 0
        wrong_clicks = 0
        total_correct_areas = len(correct_areas)
        max_score = float(total_correct_areas)

        for click in clicks:
            cx = click.get("x", 0)
            cy = click.get("y", 0)
            is_correct_click = False
            for area in correct_areas:
                if area.contains_point(cx, cy):
                    is_correct_click = True
                    break
            if is_correct_click:
                correct_clicks += 1
            else:
                wrong_clicks += 1

        raw_score = correct_clicks - wrong_clicks
        score = max(0.0, float(raw_score))
        return score, max_score


# ---------------------------------------------------------------------------
# GRID: correct = +1, incorrect = -1, min 0
# Used by: Grid Selection (4)
# Per SRS feedback: 'Total mark (five correct answers) should be 5.
# Negative marking should be (-1) for each incorrect option selected.'
# ---------------------------------------------------------------------------


def _score_grid(
    question: Question, raw_answer: dict, sub_question_index: int = 0
) -> tuple[float, float]:
    """Score grid selection: each correct selected = +1, each incorrect = -1, min 0.

    raw_answer = {"selected_cells": [{"r": 0, "c": 1}, ...]}
    Correct cells are options with is_correct=True.
    """
    opts_qs = question.options.filter(option_type="DRAG_POOL")
    if sub_question_index:
        opts_qs = opts_qs.filter(sub_question_index=sub_question_index)
    options = list(opts_qs)
    if not options:
        return 0.0, 0.0

    correct_options = [o for o in options if o.is_correct]
    max_score = float(len(correct_options))

    selected_cells = raw_answer.get("selected_cells", [])
    if not selected_cells:
        return 0.0, max_score

    # Map selected cells to option IDs by (row, col) order
    # Grid cells are options ordered by their 'order' field
    # The frontend sends selected_cells as [{"r": row, "c": col}, ...]
    # We need to map these to option IDs
    correct_count = 0
    wrong_count = 0

    # Build a grid position -> option mapping
    # Options are ordered: row 0 = options[0..cols-1], row 1 = options[cols..2*cols-1], etc.
    grid_cols = question.grid_cols or 1

    for cell in selected_cells:
        r = cell.get("r", 0)
        c = cell.get("c", 0)
        idx = r * grid_cols + c
        if 0 <= idx < len(options):
            if options[idx].is_correct:
                correct_count += 1
            else:
                wrong_count += 1
        else:
            wrong_count += 1

    raw_score = correct_count - wrong_count
    score = max(0.0, float(raw_score))
    return score, max_score


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

    For multi-sub-question questions: the parent question is a wrapper
    with no score of its own. Each sub-question has its own
    QuestionAttempt (sub_question_index 0..N-1), scored independently
    (0 or 1 for binary MCQ). The section total is the sum of all
    sub-question scores. Unattempted sub-questions get placeholder
    attempts with score=0 so the max_score is correct.

    Per SRS 03_assessment_configuration.json §3.2 (Score Summation Rules):
      - Question level scores are added up for Level4-Summary Score
      - Level4-summary scores are added up for Level3-Summary Score
      - Level3-summary scores are added up for Level2-Summary Score
      - Level2-summary scores are added up for Level1-Summary Score

    This function creates SectionScore records for EVERY section in the
    assessment's hierarchy — leaf sections get direct question scores,
    parent sections get the sum of their children's scores.
    """
    # ── Step 0: Ensure all sub-question attempts exist ──
    # For multi-sub-question questions, create placeholder attempts
    # for any sub-questions the candidate didn't answer. This ensures
    # the max_score reflects ALL sub-questions (e.g., 5), not just the
    # ones the candidate attempted (e.g., 3).
    from .models import AssessmentQuestion, AssessmentSection, QuestionAttempt, SectionScore

    for aq in AssessmentQuestion.objects.filter(
        section__assessment=session.assessment
    ).select_related("question"):
        question = aq.question
        n_subs = getattr(question, "sub_question_count", 1) or 1
        if n_subs > 1:
            for sqi in range(n_subs):
                QuestionAttempt.objects.get_or_create(
                    session=session,
                    question=question,
                    sub_question_index=sqi,
                    defaults={
                        "section": aq.section,
                        "status": "not_attempted",
                    },
                )

    attempts = session.question_attempts.select_related("question", "section").all()

    # ── Step 1: Score each attempt and aggregate by leaf section ──
    # Build a lookup of AssessmentQuestion overrides so we can apply
    # score_override if the author set a custom max score per question.
    override_map: dict[tuple[int, int], float] = {}
    for aq in AssessmentQuestion.objects.filter(
        section__assessment=session.assessment,
        score_override__isnull=False,
    ):
        override_map[(aq.question_id, aq.sub_question_index)] = aq.score_override

    # Build a section_tag → AssessmentSection map for psychometric routing.
    # Options carry a portable ``section_tag`` label (set at question creation);
    # when scored, each option's contribution must be routed to the
    # AssessmentSection whose title matches the tag. Unresolved tags fall back
    # to the attempt's own section (the question's assigned parent section).
    all_assessment_sections = list(AssessmentSection.objects.filter(assessment=session.assessment))
    tag_to_section_id: dict[str, int | None] = {s.title: s.id for s in all_assessment_sections}

    leaf_scores: dict[int, dict] = {}  # section_id -> {raw, max}
    total_raw = 0.0
    total_max = 0.0

    for attempt in attempts:
        # Check for score_override on this question
        override_key = (attempt.question_id, attempt.sub_question_index)
        override_max = override_map.get(override_key)

        if attempt.status != "attempted" or not attempt.raw_answer:
            attempt.score = 0.0
            attempt.max_score = (
                override_max
                if override_max is not None
                else _get_max_score(attempt.question, attempt.sub_question_index)
            )
            attempt.save(update_fields=["score", "max_score"])
        else:
            score, max_score = score_question(
                attempt.question, attempt.raw_answer, attempt.sub_question_index
            )
            # Apply score_override: if set, use it as the max_score and
            # scale the raw score proportionally
            if override_max is not None and max_score > 0:
                score = round(score * (override_max / max_score), 4)
                max_score = override_max
            attempt.score = score
            attempt.max_score = max_score
            attempt.save(update_fields=["score", "max_score"])

        # Even unattempted questions contribute to the section's max_score
        # (so the candidate sees how many points were available)
        total_raw += attempt.score or 0.0
        total_max += attempt.max_score or 0.0

        # ── Psychometric per-section routing (Report 2) ──
        # For psychometric types, split the attempt's score across the
        # sections each option is tagged to (via score_question_by_section).
        # Non-psychometric types aggregate the whole attempt into one section.
        by_section = score_question_by_section(
            attempt.question,
            attempt.raw_answer if attempt.status == "attempted" else None,
            attempt.sub_question_index,
        )
        if by_section:
            for tag, (raw, mx) in by_section.items():
                target_sid = tag_to_section_id.get(tag) if tag else None
                if target_sid is None:
                    # Unresolved tag → fall back to the attempt's own section
                    target_sid = attempt.section_id
                if target_sid is None:
                    continue
                if target_sid not in leaf_scores:
                    leaf_scores[target_sid] = {"raw": 0.0, "max": 0.0}
                leaf_scores[target_sid]["raw"] += raw
                leaf_scores[target_sid]["max"] += mx
        else:
            sid = attempt.section_id
            if sid:
                if sid not in leaf_scores:
                    leaf_scores[sid] = {"raw": 0.0, "max": 0.0}
                leaf_scores[sid]["raw"] += attempt.score or 0.0
                leaf_scores[sid]["max"] += attempt.max_score or 0.0

    # ── Step 2: Build the section hierarchy for the assessment ──
    # Load all sections (ordered deepest-first for the roll-up pass below)
    all_sections = list(
        AssessmentSection.objects.filter(assessment=session.assessment).order_by("level", "order")
    )

    # ── Step 3: Roll up scores from leaf to root ──
    # Start with leaf scores, then propagate up the hierarchy.
    # Process sections from deepest level to shallowest so children are
    # always computed before parents.
    section_scores: dict[int, dict] = dict(leaf_scores)  # copy leaf scores

    for section in sorted(all_sections, key=lambda s: -s.level):
        if section.id in section_scores:
            # Already has a score (leaf or already computed) — propagate to parent
            parent_id = section.parent_id
            if parent_id is not None:
                if parent_id not in section_scores:
                    section_scores[parent_id] = {"raw": 0.0, "max": 0.0}
                section_scores[parent_id]["raw"] += section_scores[section.id]["raw"]
                section_scores[parent_id]["max"] += section_scores[section.id]["max"]
        else:
            # No direct questions and not yet computed — initialize to 0
            # (will be populated by children if any exist)
            section_scores[section.id] = {"raw": 0.0, "max": 0.0}

    # Second pass: for any parent that still has 0 but has children with
    # scores, aggregate from children. This handles sections where the
    # parent wasn't reached in the first pass (e.g. a Level 2 with no
    # direct Level 4 descendants that were attempted).
    for section in sorted(all_sections, key=lambda s: -s.level):
        parent_id = section.parent_id
        if parent_id is None:
            continue
        if parent_id not in section_scores:
            section_scores[parent_id] = {"raw": 0.0, "max": 0.0}

    # ── Step 4: Create/update SectionScore records for ALL sections ──
    # This ensures Level 1/2/3 parent sections get a SectionScore even if
    # they have no direct question attempts — their score is the sum of
    # their children's scores.
    for section in all_sections:
        scores = section_scores.get(section.id, {"raw": 0.0, "max": 0.0})
        SectionScore.objects.update_or_create(
            session=session,
            section=section,
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
