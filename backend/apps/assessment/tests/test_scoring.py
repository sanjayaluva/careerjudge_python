"""Tests for the Assessment scoring engine.

Verifies all 9 scoring modes work correctly per SRS 00_scoring_rules.json.
"""

from django.test import TestCase

from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment, AssessmentSection, AssessmentSession, QuestionAttempt
from apps.assessment.scoring import (
    _get_max_score,
    calculate_session_scores,
    score_question,
)

from .factories import (
    UserFactory,
    get_or_create_role,
    make_fitb_question,
    make_forced_choice_question,
    make_match_question,
    make_mcq_question,
    make_rank_question,
    make_rating_question,
)


class ScoringTestBase(TestCase):
    """Ensure default roles exist so UserFactory can assign them."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        get_or_create_default_roles()
        cls.individual_role = get_or_create_role("individual", is_system=True)


class TestBinaryScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_mcq_question(self.user, scoring_type="BINARY")

    def test_correct_answer_scores_1(self):
        correct = self.q.options.filter(is_correct=True).first()
        score, max_score = score_question(self.q, {"selected_option_ids": [correct.id]})
        assert score == 1.0
        assert max_score == 1.0

    def test_wrong_answer_scores_0(self):
        wrong = self.q.options.filter(is_correct=False).first()
        score, _ = score_question(self.q, {"selected_option_ids": [wrong.id]})
        assert score == 0.0

    def test_no_answer_scores_0(self):
        score, max_score = score_question(self.q, None)
        assert score == 0.0
        assert max_score == 1.0


class TestPartialScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_fitb_question(self.user, scoring_type="PARTIAL")

    def test_all_correct_scores_max(self):
        score, max_score = score_question(self.q, {"answers": ["Paris", "France"]})
        assert score == 2.0
        assert max_score == 2.0

    def test_one_correct_scores_half(self):
        score, _ = score_question(self.q, {"answers": ["Paris", "Wrong"]})
        assert score == 1.0

    def test_case_insensitive_by_default(self):
        score, _ = score_question(self.q, {"answers": ["paris", "FRANCE"]})
        assert score == 2.0

    def test_none_answer_scores_0(self):
        score, max_score = score_question(self.q, None)
        assert score == 0.0
        assert max_score == 2.0


class TestRatingScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_rating_question(self.user)  # 5-point, FORWARD

    def test_forward_direction_leftmost_is_highest(self):
        # rating=1 → score=5 (forward: leftmost=highest)
        score, max_score = score_question(self.q, {"rating": 1})
        assert score == 5.0
        assert max_score == 5.0

    def test_forward_direction_rightmost_is_lowest(self):
        score, _ = score_question(self.q, {"rating": 5})
        assert score == 1.0

    def test_no_rating_scores_0(self):
        score, _ = score_question(self.q, {"rating": 0})
        assert score == 0.0


class TestRankScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_rank_question(self.user)  # 4 options, scoring_type=RANK

    def test_perfect_order_max_score(self):
        # The correct order is the saved option order: items 1, 2, 3, 4
        options = list(self.q.options.all().order_by("order"))
        perfect = [o.id for o in options]
        score, max_score = score_question(self.q, {"ranking": perfect})
        # Max score for n=4 is 4*3/2 = 6 (number of unique pairs)
        assert score == max_score
        assert max_score == 6.0

    def test_zero_score_for_no_answer(self):
        score, max_score = score_question(self.q, None)
        assert score == 0.0
        assert max_score == 6.0


class TestForcedChoiceScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_forced_choice_question(self.user, two_level=False)
        # Options: A=2.0, B=3.0

    def test_select_high_score_option(self):
        opt_b = self.q.options.get(text_value="Option B")
        score, max_score = score_question(self.q, {"selected_option_id": opt_b.id})
        assert score == 3.0
        assert max_score == 3.0

    def test_select_low_score_option(self):
        opt_a = self.q.options.get(text_value="Option A")
        score, max_score = score_question(self.q, {"selected_option_id": opt_a.id})
        assert score == 2.0
        assert max_score == 3.0

    def test_no_selection_scores_0(self):
        score, _ = score_question(self.q, {})
        assert score == 0.0


class TestForcedChoiceRatedScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_forced_choice_question(self.user, two_level=True)
        # Options: A=2.0, B=3.0, max_rating=5

    def test_score_is_predefined_times_rating(self):
        opt_b = self.q.options.get(text_value="Option B")
        score, max_score = score_question(self.q, {"selected_option_id": opt_b.id, "rating": 4})
        assert score == 12.0  # 3.0 x 4
        assert max_score == 15.0  # 3.0 x 5

    def test_no_rating_scores_0(self):
        opt_b = self.q.options.get(text_value="Option B")
        score, _ = score_question(self.q, {"selected_option_id": opt_b.id, "rating": 0})
        assert score == 0.0


class TestMatchScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_match_question(self.user)  # 3 pairs

    def test_all_correct_pairs_scores_max(self):
        # Each A option has match_pair_id matching its B option
        a_opts = list(self.q.options.filter(option_type="MATCH_A").order_by("match_pair_id"))
        b_opts = list(self.q.options.filter(option_type="MATCH_B").order_by("match_pair_id"))
        # Pair them up correctly
        pairs = [{"a_id": a.id, "b_id": b.id} for a, b in zip(a_opts, b_opts, strict=False)]
        score, max_score = score_question(self.q, {"pairs": pairs})
        assert score == 3.0
        assert max_score == 3.0

    def test_one_wrong_pair(self):
        a_opts = list(self.q.options.filter(option_type="MATCH_A").order_by("match_pair_id"))
        b_opts = list(self.q.options.filter(option_type="MATCH_B").order_by("match_pair_id"))
        # Swap first two B's
        pairs = [
            {"a_id": a_opts[0].id, "b_id": b_opts[1].id},  # wrong
            {"a_id": a_opts[1].id, "b_id": b_opts[0].id},  # wrong
            {"a_id": a_opts[2].id, "b_id": b_opts[2].id},  # correct
        ]
        score, _ = score_question(self.q, {"pairs": pairs})
        assert score == 1.0


class TestGetMaxScore(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)

    def test_binary_max_1(self):
        q = make_mcq_question(self.user, scoring_type="BINARY")
        assert _get_max_score(q) == 1.0

    def test_rating_max_5(self):
        q = make_rating_question(self.user)
        assert _get_max_score(q) == 5.0

    def test_partial_max_options_count(self):
        q = make_fitb_question(self.user, scoring_type="PARTIAL")
        assert _get_max_score(q) == 2.0  # 2 fields

    def test_rank_max_n_choose_2_pairs(self):
        q = make_rank_question(self.user)  # 4 options
        assert _get_max_score(q) == 6.0  # 4*3/2

    def test_forced_choice_max_is_highest_predefined(self):
        q = make_forced_choice_question(self.user, two_level=False)
        assert _get_max_score(q) == 3.0  # max predefined_score


class TestCalculateSessionScores(ScoringTestBase):
    """End-to-end test: create a session, answer questions, calculate scores."""

    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.assessment = Assessment.objects.create(title="Test Assessment", status="published")
        self.section = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 1", level=1, order=1
        )
        # Create two confirmed questions
        self.q1 = make_mcq_question(self.user, scoring_type="BINARY")
        self.q2 = make_rating_question(self.user)
        # Assign to section
        from apps.assessment.models import AssessmentQuestion

        AssessmentQuestion.objects.create(section=self.section, question=self.q1, order=1)
        AssessmentQuestion.objects.create(section=self.section, question=self.q2, order=2)

        # Create session and attempts
        self.session = AssessmentSession.objects.create(
            assessment=self.assessment, candidate=self.user, status="active"
        )
        self.attempt1 = QuestionAttempt.objects.create(
            session=self.session, question=self.q1, section=self.section
        )
        self.attempt2 = QuestionAttempt.objects.create(
            session=self.session, question=self.q2, section=self.section
        )

    def test_calculate_scores_updates_session_totals(self):
        # Answer q1 correctly (binary → 1.0)
        correct_opt = self.q1.options.filter(is_correct=True).first()
        self.attempt1.raw_answer = {"selected_option_ids": [correct_opt.id]}
        self.attempt1.status = "attempted"
        self.attempt1.save()

        # Answer q2 with rating=1 (forward → score=5)
        self.attempt2.raw_answer = {"rating": 1}
        self.attempt2.status = "attempted"
        self.attempt2.save()

        calculate_session_scores(self.session)
        self.session.refresh_from_db()

        assert self.session.total_score == 6.0  # 1 + 5
        assert self.session.max_score == 6.0  # 1 + 5
        assert self.session.percentage == 100.0

    def test_creates_section_scores(self):
        correct_opt = self.q1.options.filter(is_correct=True).first()
        self.attempt1.raw_answer = {"selected_option_ids": [correct_opt.id]}
        self.attempt1.status = "attempted"
        self.attempt1.save()

        self.attempt2.raw_answer = {"rating": 3}  # score = 5-3+1 = 3
        self.attempt2.status = "attempted"
        self.attempt2.save()

        calculate_session_scores(self.session)

        from apps.assessment.models import SectionScore

        ss = SectionScore.objects.get(session=self.session, section=self.section)
        assert ss.raw_score == 4.0  # 1 + 3
        assert ss.max_score == 6.0
        assert ss.percentage == 66.67

    def test_unattempted_questions_score_zero(self):
        # Don't answer either question — both should be 0
        calculate_session_scores(self.session)
        self.session.refresh_from_db()
        assert self.session.total_score == 0.0
        assert self.session.percentage == 0

    def test_increments_exposure_count(self):
        correct_opt = self.q1.options.filter(is_correct=True).first()
        self.attempt1.raw_answer = {"selected_option_ids": [correct_opt.id]}
        self.attempt1.status = "attempted"
        self.attempt1.save()

        calculate_session_scores(self.session)

        self.q1.refresh_from_db()
        self.q2.refresh_from_db()
        assert self.q1.exposure_count == 1
        assert self.q2.exposure_count == 1

    def test_auto_deactivates_at_exposure_limit(self):
        # Set exposure limit low
        from apps.question_bank.models import Question

        Question.objects.filter(id=self.q1.id).update(exposure_limit=1)

        correct_opt = self.q1.options.filter(is_correct=True).first()
        self.attempt1.raw_answer = {"selected_option_ids": [correct_opt.id]}
        self.attempt1.status = "attempted"
        self.attempt1.save()

        calculate_session_scores(self.session)

        self.q1.refresh_from_db()
        assert self.q1.exposure_count == 1
        assert self.q1.is_active is False
