"""Tests for the Assessment scoring engine.

Verifies all 9 scoring modes work correctly per SRS 00_scoring_rules.json.
"""

from django.test import TestCase

from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
    QuestionAttempt,
)
from apps.assessment.scoring import (
    _get_max_score,
    calculate_session_scores,
    score_question,
    score_question_by_section,
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

    def test_full_ranking_scores_sum_to_n(self):
        # Per Report 2 §1: rank 1 → N, rank 2 → N-1, ... rank N → 1.
        # For N=4 the total = 4+3+2+1 = 10. Max = N = 4.
        options = list(self.q.options.all().order_by("order"))
        ranking = [o.id for o in options]
        score, max_score = score_question(self.q, {"ranking": ranking})
        assert score == 10.0  # 4 + 3 + 2 + 1
        assert max_score == 4.0

    def test_rank_value_is_n_minus_rank_plus_one(self):
        # The first option in the ranking list (rank 1) → score N (4),
        # the last (rank 4) → score 1.
        options = list(self.q.options.all().order_by("order"))
        ranking = [o.id for o in options]
        by_section = score_question_by_section(self.q, {"ranking": ranking})
        # First-ranked option tagged "Section 1" → 4
        assert by_section[options[0].section_tag][0] == 4.0
        # Last-ranked option tagged "Section 4" → 1
        assert by_section[options[3].section_tag][0] == 1.0

    def test_zero_score_for_no_answer(self):
        score, max_score = score_question(self.q, None)
        assert score == 0.0
        assert max_score == 4.0

    def test_by_section_returns_none_for_non_psychometric(self):
        from apps.assessment.tests.factories import make_mcq_question

        q = make_mcq_question(self.user, scoring_type="BINARY")
        assert score_question_by_section(q, {"selected_option_ids": [1]}) is None


class TestForcedChoiceScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_forced_choice_question(self.user, two_level=False)
        # Options: A (Section A) sel=2.0/non=0.0; B (Section B) sel=3.0/non=1.0

    def test_selected_earns_selection_non_selected_earns_non_selection(self):
        # Select B -> B earns selection_score 3.0; A earns non_selection_score 0.0.
        opt_b = self.q.options.get(text_value="Option B")
        score, max_score = score_question(self.q, {"selected_option_id": opt_b.id})
        assert score == 3.0 + 0.0  # B's selection + A's non-selection
        # max = max(selection, non-selection) across the pair = max(2, 3, 0, 1) = 3
        assert max_score == 3.0

    def test_selecting_lower_option_still_pays_non_selection_to_other(self):
        # Select A → A earns 2.0; B earns its non_selection_score 1.0.
        opt_a = self.q.options.get(text_value="Option A")
        score, _ = score_question(self.q, {"selected_option_id": opt_a.id})
        assert score == 2.0 + 1.0  # A's selection + B's non-selection

    def test_scores_route_to_each_options_own_section(self):
        opt_b = self.q.options.get(text_value="Option B")
        by_section = score_question_by_section(self.q, {"selected_option_id": opt_b.id})
        # Section A (the non-selected option) → non_selection_score 0.0
        assert by_section["Section A"][0] == 0.0
        # Section B (the selected option) → selection_score 3.0
        assert by_section["Section B"][0] == 3.0

    def test_no_selection_scores_0(self):
        score, _ = score_question(self.q, {})
        assert score == 0.0


class TestForcedChoiceRatedScoring(ScoringTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.q = make_forced_choice_question(self.user, two_level=True)
        # Options: A (Section A) sel=2.0/non=0.0; B (Section B) sel=3.0/non=1.0
        # max_rating = 5

    def test_selected_score_times_rating_plus_non_selection(self):
        # Select B (rating 4) → B earns 3.0*4 = 12; A earns non_selection 0.0.
        opt_b = self.q.options.get(text_value="Option B")
        score, max_score = score_question(self.q, {"selected_option_id": opt_b.id, "rating": 4})
        assert score == 12.0 + 0.0
        # max = max(selection * max_rating, non_selection) = max(2*5, 3*5, 0, 1) = 15
        assert max_score == 15.0

    def test_non_selected_option_still_earns_its_non_selection(self):
        # Select A (rating 5) → A earns 2.0*5 = 10; B earns non_selection 1.0.
        opt_a = self.q.options.get(text_value="Option A")
        score, _ = score_question(self.q, {"selected_option_id": opt_a.id, "rating": 5})
        assert score == 10.0 + 1.0

    def test_by_section_routes_rated_scores(self):
        opt_a = self.q.options.get(text_value="Option A")
        by_section = score_question_by_section(
            self.q, {"selected_option_id": opt_a.id, "rating": 5}
        )
        # Section A (selected) → 2.0 * 5 = 10
        assert by_section["Section A"][0] == 10.0
        # Section B (non-selected) → non_selection_score 1.0
        assert by_section["Section B"][0] == 1.0

    def test_no_rating_selected_option_scores_zero(self):
        # Rating required for the selected option → it scores 0; the
        # non-selected option still earns its non_selection_score.
        opt_b = self.q.options.get(text_value="Option B")
        score, _ = score_question(self.q, {"selected_option_id": opt_b.id, "rating": 0})
        # B (selected, no rating) → 0; A (non-selected) → non_selection 0.0
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

    def test_rank_max_equals_n(self):
        # Per Report 2 §1: rank max = N (rank-1 → N is the per-option cap).
        q = make_rank_question(self.user)  # 4 options
        assert _get_max_score(q) == 4.0

    def test_forced_choice_max_is_best_selection_or_non_selection(self):
        # Options: A sel=2/non=0; B sel=3/non=1 → max = 3
        q = make_forced_choice_question(self.user, two_level=False)
        assert _get_max_score(q) == 3.0


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

    def test_hierarchical_section_score_rollup(self):
        """Per SRS §3.2: scores roll up L4 → L3 → L2 → L1.

        Creates a 4-level hierarchy:
          L1: Root Variable
            L2: Sub-Variable A
              L3: Sub-Sub A1
                L4: Leaf A1a (question attached here)
            L2: Sub-Variable B
              L3: Sub-Sub B1
                L4: Leaf B1a (question attached here)

        After scoring, every level should have a SectionScore — parents
        get the sum of their children's scores.
        """
        from apps.assessment.models import AssessmentQuestion, SectionScore

        # Build the hierarchy
        l1 = AssessmentSection.objects.create(
            assessment=self.assessment, title="Root Variable", level=1, order=1
        )
        l2a = AssessmentSection.objects.create(
            assessment=self.assessment, parent=l1, title="Sub-Variable A", level=2, order=1
        )
        l3a = AssessmentSection.objects.create(
            assessment=self.assessment, parent=l2a, title="Sub-Sub A1", level=3, order=1
        )
        l4a = AssessmentSection.objects.create(
            assessment=self.assessment, parent=l3a, title="Leaf A1a", level=4, order=1
        )
        l2b = AssessmentSection.objects.create(
            assessment=self.assessment, parent=l1, title="Sub-Variable B", level=2, order=2
        )
        l3b = AssessmentSection.objects.create(
            assessment=self.assessment, parent=l2b, title="Sub-Sub B1", level=3, order=1
        )
        l4b = AssessmentSection.objects.create(
            assessment=self.assessment, parent=l3b, title="Leaf B1b", level=4, order=1
        )

        # Attach one MCQ to each leaf (L4)
        q_a = make_mcq_question(self.user, scoring_type="BINARY")
        q_b = make_mcq_question(self.user, scoring_type="BINARY")
        AssessmentQuestion.objects.create(section=l4a, question=q_a, order=1)
        AssessmentQuestion.objects.create(section=l4b, question=q_b, order=1)

        # Create attempts — answer both correctly (each scores 1.0)
        from apps.assessment.models import QuestionAttempt

        correct_a = q_a.options.filter(is_correct=True).first()
        correct_b = q_b.options.filter(is_correct=True).first()
        QuestionAttempt.objects.create(
            session=self.session,
            question=q_a,
            section=l4a,
            status="attempted",
            raw_answer={"selected_option_ids": [correct_a.id]},
        )
        QuestionAttempt.objects.create(
            session=self.session,
            question=q_b,
            section=l4b,
            status="attempted",
            raw_answer={"selected_option_ids": [correct_b.id]},
        )

        calculate_session_scores(self.session)

        # Verify ALL sections have SectionScore records (7 from this hierarchy
        # + 1 from setUp's self.section with its 2 questions = 8 total)
        scores = {s.section_id: s for s in SectionScore.objects.filter(session=self.session)}
        assert len(scores) == 8, f"Expected 8 section scores, got {len(scores)}"

        # L4 leaves: each scored 1.0 / 1.0
        assert scores[l4a.id].raw_score == 1.0
        assert scores[l4a.id].max_score == 1.0
        assert scores[l4b.id].raw_score == 1.0
        assert scores[l4b.id].max_score == 1.0

        # L3: sum of children (1 child each, so 1.0 / 1.0)
        assert scores[l3a.id].raw_score == 1.0
        assert scores[l3a.id].max_score == 1.0
        assert scores[l3b.id].raw_score == 1.0
        assert scores[l3b.id].max_score == 1.0

        # L2: sum of children (1 child each, so 1.0 / 1.0)
        assert scores[l2a.id].raw_score == 1.0
        assert scores[l2a.id].max_score == 1.0
        assert scores[l2b.id].raw_score == 1.0
        assert scores[l2b.id].max_score == 1.0

        # L1 root: sum of both L2 children (2.0 / 2.0)
        assert scores[l1.id].raw_score == 2.0
        assert scores[l1.id].max_score == 2.0


class TestPsychometricSectionAggregation(ScoringTestBase):
    """Per Report 2: psychometric option scores must route to each option's
    tagged section. Mirrors the SRS §1 example: two rank questions whose
    options are tagged to shared sections; Section 1's summary is the sum of
    rank values received by ALL options tagged to Section 1 across questions.
    """

    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.assessment = Assessment.objects.create(
            title="Psychometric Test", status="published", assessment_type="psychometric"
        )
        # 4 sections — matching the 4 options per rank question.
        self.s1 = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 1", level=1, order=1
        )
        self.s2 = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 2", level=1, order=2
        )
        self.s3 = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 3", level=1, order=3
        )
        self.s4 = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 4", level=1, order=4
        )
        # A "carrier" section the questions are assigned to (their own
        # section_id) — psychometric routing overrides this by splitting
        # scores into s1..s4 via the tags.
        self.carrier = AssessmentSection.objects.create(
            assessment=self.assessment, title="Carrier", level=1, order=5
        )

        # Two rank questions. Each has 4 options tagged to Section 1..4.
        from apps.question_bank.models import Question, ResponseOption

        self.q1 = Question.objects.create(
            category_id=None,
            question_type="RANK_SIMPLE",
            question_title="Q1",
            question_text_1="Rank Q1",
            scoring_type="RANK",
            status="confirmed",
            created_by=self.user,
        )
        self.q1_opts = []
        for i in range(1, 5):
            o = ResponseOption.objects.create(
                question=self.q1,
                option_type="RANK",
                text_value=f"Q1 Item {i}",
                section_tag=f"Section {i}",
                order=i,
            )
            self.q1_opts.append(o)
        AssessmentQuestion.objects.create(section=self.carrier, question=self.q1, order=1)

        self.q2 = Question.objects.create(
            category_id=None,
            question_type="RANK_SIMPLE",
            question_title="Q2",
            question_text_1="Rank Q2",
            scoring_type="RANK",
            status="confirmed",
            created_by=self.user,
        )
        self.q2_opts = []
        for i in range(1, 5):
            o = ResponseOption.objects.create(
                question=self.q2,
                option_type="RANK",
                text_value=f"Q2 Item {i}",
                section_tag=f"Section {i}",
                order=i,
            )
            self.q2_opts.append(o)
        AssessmentQuestion.objects.create(section=self.carrier, question=self.q2, order=2)

        self.session = AssessmentSession.objects.create(
            assessment=self.assessment, candidate=self.user, status="active"
        )

    def test_section_summary_sums_across_questions(self):
        # Rank Q1 so the option tagged "Section 1" (q1_opts[0]) is ranked 1 → 4.
        # Rank Q2 so the option tagged "Section 1" (q2_opts[0]) is ranked 1 → 4.
        # Section 1 summary = 4 + 4 = 8 (matches SRS §1 worked example).
        QuestionAttempt.objects.create(
            session=self.session,
            question=self.q1,
            section=self.carrier,
            status="attempted",
            raw_answer={
                "ranking": [
                    self.q1_opts[0].id,
                    self.q1_opts[1].id,
                    self.q1_opts[2].id,
                    self.q1_opts[3].id,
                ]
            },
        )
        QuestionAttempt.objects.create(
            session=self.session,
            question=self.q2,
            section=self.carrier,
            status="attempted",
            raw_answer={
                "ranking": [
                    self.q2_opts[0].id,
                    self.q2_opts[1].id,
                    self.q2_opts[2].id,
                    self.q2_opts[3].id,
                ]
            },
        )

        calculate_session_scores(self.session)

        from apps.assessment.models import SectionScore

        ss1 = SectionScore.objects.get(session=self.session, section=self.s1)
        assert ss1.raw_score == 8.0  # 4 (Q1 opt tagged Section 1, rank 1) + 4 (Q2)

    def test_section_max_does_not_explode_across_tags(self):
        """Regression: each option's max must be assigned to its OWN tag, not
        added to every tag. With 4 distinct tags the per-section max should be
        N (4), not 4*N (16)."""
        QuestionAttempt.objects.create(
            session=self.session,
            question=self.q1,
            section=self.carrier,
            status="attempted",
            raw_answer={
                "ranking": [
                    self.q1_opts[0].id,
                    self.q1_opts[1].id,
                    self.q1_opts[2].id,
                    self.q1_opts[3].id,
                ]
            },
        )

        calculate_session_scores(self.session)

        from apps.assessment.models import SectionScore

        for sec in (self.s1, self.s2, self.s3, self.s4):
            ss = SectionScore.objects.get(session=self.session, section=sec)
            # Each section has exactly one option (max = N = 4), not 16.
            assert (
                ss.max_score == 4.0
            ), f"Section {sec.title} max_score={ss.max_score}, expected 4.0"

    def test_unresolved_tag_falls_back_to_attempt_section(self):
        # If a tag has no matching AssessmentSection, the score falls back to
        # the attempt's own section (carrier) instead of being lost.
        from apps.question_bank.models import ResponseOption

        # Retag q1's first option with an unknown tag
        ResponseOption.objects.filter(id=self.q1_opts[0].id).update(section_tag="Unknown")
        QuestionAttempt.objects.create(
            session=self.session,
            question=self.q1,
            section=self.carrier,
            status="attempted",
            raw_answer={
                "ranking": [
                    self.q1_opts[0].id,
                    self.q1_opts[1].id,
                    self.q1_opts[2].id,
                    self.q1_opts[3].id,
                ]
            },
        )

        calculate_session_scores(self.session)

        from apps.assessment.models import SectionScore

        # The "Unknown"-tagged option's rank-1 score (4) lands in carrier
        carrier_ss = SectionScore.objects.get(session=self.session, section=self.carrier)
        assert carrier_ss.raw_score == 4.0


class TestForcedChoiceSectionAggregation(ScoringTestBase):
    """Per Report 2 §3: a forced-choice pair posts TWO scores — one to each
    option's own section (selected → selection_score, non-selected →
    non_selection_score)."""

    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.assessment = Assessment.objects.create(
            title="Forced Choice Test", status="published", assessment_type="psychometric"
        )
        self.sec_a = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section A", level=1, order=1
        )
        self.sec_b = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section B", level=1, order=2
        )
        self.carrier = AssessmentSection.objects.create(
            assessment=self.assessment, title="Carrier", level=1, order=3
        )
        self.q = make_forced_choice_question(self.user, two_level=False)
        AssessmentQuestion.objects.create(section=self.carrier, question=self.q, order=1)
        self.session = AssessmentSession.objects.create(
            assessment=self.assessment, candidate=self.user, status="active"
        )

    def test_both_sections_receive_a_score(self):
        opt_b = self.q.options.get(text_value="Option B")  # Section B, sel=3/non=1
        QuestionAttempt.objects.create(
            session=self.session,
            question=self.q,
            section=self.carrier,
            status="attempted",
            raw_answer={"selected_option_id": opt_b.id},  # select B
        )

        calculate_session_scores(self.session)

        from apps.assessment.models import SectionScore

        # Section A (non-selected option A) → non_selection_score 0.0
        ss_a = SectionScore.objects.get(session=self.session, section=self.sec_a)
        assert ss_a.raw_score == 0.0
        # Section B (selected option B) → selection_score 3.0
        ss_b = SectionScore.objects.get(session=self.session, section=self.sec_b)
        assert ss_b.raw_score == 3.0
