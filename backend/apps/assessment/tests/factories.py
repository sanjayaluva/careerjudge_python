"""Test factories for the Assessment module.

Reuses ``UserFactory`` and role helpers from the accounts tests, and adds
question-bank factories for each question type the assessment scoring engine
needs to be tested against.
"""

import factory

from apps.accounts.models import Role
from apps.accounts.tests.factories import UserFactory  # noqa: F401  (re-exported)
from apps.question_bank.models import Category, CorrectAnswer, Question, ResponseOption


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    description = "Test category"


def _make_question(created_by, question_type, scoring_type, title, **extra):
    """Helper: create a confirmed Question with sensible defaults."""
    defaults = {
        "category": CategoryFactory.create(),
        "question_type": question_type,
        "question_title": title,
        "question_text_1": "Test question text",
        "scoring_type": scoring_type,
        "status": "confirmed",
        "created_by": created_by,
    }
    defaults.update(extra)
    return Question.objects.create(**defaults)


def make_mcq_question(created_by, scoring_type="BINARY", confirmed=True):
    """Create a confirmed MCQ question with 4 options (1 correct)."""
    q = _make_question(
        created_by,
        "MCQ_TEXT_IMAGE",
        scoring_type,
        "MCQ Question",
        question_text_1="What is 2+2?",
    )
    ResponseOption.objects.create(
        question=q, option_type="TEXT", text_value="3", is_correct=False, order=1
    )
    ResponseOption.objects.create(
        question=q, option_type="TEXT", text_value="4", is_correct=True, order=2
    )
    ResponseOption.objects.create(
        question=q, option_type="TEXT", text_value="5", is_correct=False, order=3
    )
    ResponseOption.objects.create(
        question=q, option_type="TEXT", text_value="6", is_correct=False, order=4
    )
    if not confirmed:
        q.status = "draft"
        q.save()
    return q


def make_fitb_question(created_by, scoring_type="PARTIAL", confirmed=True):
    """Create a confirmed FITB multi-field question with 2 fields."""
    q = _make_question(
        created_by,
        "FITB_MULTI_FIELD",
        scoring_type,
        "FITB Question",
        question_text_1="Fill in the blanks:",
    )
    opt1 = ResponseOption.objects.create(
        question=q, option_type="TEXT", text_value="Field 1", order=1
    )
    CorrectAnswer.objects.create(response_option=opt1, answer_text="Paris")
    opt2 = ResponseOption.objects.create(
        question=q, option_type="TEXT", text_value="Field 2", order=2
    )
    CorrectAnswer.objects.create(response_option=opt2, answer_text="France")
    if not confirmed:
        q.status = "draft"
        q.save()
    return q


def make_rating_question(created_by, confirmed=True):
    """Create a rating scale question (5-point, forward direction)."""
    return _make_question(
        created_by,
        "STANDARD_RATING_SCALE",
        "RATING",
        "Rating Question",
        question_text_1="Rate this statement:",
        rating_scale_points=5,
        rating_direction="FORWARD",
    )


def make_rank_question(created_by, confirmed=True):
    """Create a rank-simple question with 4 options."""
    q = _make_question(
        created_by,
        "RANK_SIMPLE",
        "RANK",
        "Rank Question",
        question_text_1="Rank these items:",
    )
    for i in range(1, 5):
        ResponseOption.objects.create(
            question=q, option_type="RANK", text_value=f"Item {i}", order=i
        )
    return q


def make_forced_choice_question(created_by, two_level=False, confirmed=True):
    """Create a forced-choice question.

    two_level=False: FORCED_CHOICE_SINGLE_LEVEL + FORCED_CHOICE scoring.
    two_level=True:  FORCED_CHOICE_TWO_LEVEL + FORCED_CHOICE_RATED scoring.
    """
    qtype = "FORCED_CHOICE_TWO_LEVEL" if two_level else "FORCED_CHOICE_SINGLE_LEVEL"
    stype = "FORCED_CHOICE_RATED" if two_level else "FORCED_CHOICE"
    extra = {"rating_scale_points": 5} if two_level else {}
    q = _make_question(
        created_by,
        qtype,
        stype,
        "Forced Choice Question",
        question_text_1="Choose one:",
        **extra,
    )
    ResponseOption.objects.create(
        question=q,
        option_type="FORCED_CHOICE",
        text_value="Option A",
        predefined_score=2.0,
        order=1,
    )
    ResponseOption.objects.create(
        question=q,
        option_type="FORCED_CHOICE",
        text_value="Option B",
        predefined_score=3.0,
        order=2,
    )
    return q


def make_match_question(created_by, confirmed=True):
    """Create a match-the-following question with 3 pairs."""
    q = _make_question(
        created_by,
        "MATCH_FOLLOWING",
        "PARTIAL",
        "Match Question",
        question_text_1="Match the following:",
    )
    # 3 pairs with match_pair_id linking A↔B
    for i in range(1, 4):
        ResponseOption.objects.create(
            question=q, option_type="MATCH_A", text_value=f"Left {i}", match_pair_id=i, order=i
        )
        ResponseOption.objects.create(
            question=q,
            option_type="MATCH_B",
            text_value=f"Right {i}",
            match_pair_id=i,
            order=i + 10,
        )
    return q


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------


def get_or_create_role(name, is_system=False):
    """Get or create a Role by name (idempotent)."""
    role, _ = Role.objects.get_or_create(
        name=name, defaults={"is_system": is_system, "is_frozen": False}
    )
    return role
