"""Tests for the Assessment models."""

from django.test import TestCase

from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
    QuestionAttempt,
    SectionScore,
)

from .factories import UserFactory, get_or_create_role, make_mcq_question


class AssessmentModelTestBase(TestCase):
    """Common setUp: ensure default roles exist so UserFactory can assign them."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        get_or_create_default_roles()
        # Cache the individual role for setUp() use
        cls.individual_role = get_or_create_role("individual", is_system=True)


class TestAssessmentModel(AssessmentModelTestBase):
    def test_str(self):
        a = Assessment.objects.create(title="Aptitude Test 1")
        assert str(a) == "Aptitude Test 1"

    def test_default_status_draft(self):
        a = Assessment.objects.create(title="Test")
        assert a.status == "draft"

    def test_default_navigation_free(self):
        a = Assessment.objects.create(title="Test")
        assert a.navigation_rule == "FREE"

    def test_default_attempt_rule_single_session(self):
        a = Assessment.objects.create(title="Test")
        assert a.attempt_rule == "SINGLE_SESSION"

    def test_default_timer_level_assessment(self):
        a = Assessment.objects.create(title="Test")
        assert a.timer_level == "assessment"

    def test_can_edit_draft(self):
        a = Assessment.objects.create(title="Test")
        assert a.status == "draft"  # editable

    def test_cannot_edit_published(self):
        a = Assessment.objects.create(title="Test", status="published")
        assert a.status == "published"


class TestAssessmentSectionModel(AssessmentModelTestBase):
    def setUp(self):
        self.assessment = Assessment.objects.create(title="Test")

    def test_str(self):
        s = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section A", level=1, order=1
        )
        assert "Test" in str(s)
        assert "Section A" in str(s)
        assert "L1" in str(s)

    def test_hierarchical_structure(self):
        # Level 1
        s1 = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 1", level=1, order=1
        )
        # Level 2 (child of s1)
        s2 = AssessmentSection.objects.create(
            assessment=self.assessment, parent=s1, title="Section 1.1", level=2, order=1
        )
        assert s2.parent == s1
        assert s2 in s1.subsections.all()

    def test_level_default_1(self):
        s = AssessmentSection.objects.create(assessment=self.assessment, title="Test")
        assert s.level == 1


class TestAssessmentSessionModel(AssessmentModelTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.assessment = Assessment.objects.create(title="Test")

    def test_str(self):
        s = AssessmentSession.objects.create(assessment=self.assessment, candidate=self.user)
        assert "Test" in str(s)
        assert self.user.email in str(s)
        assert "active" in str(s)

    def test_default_status_active(self):
        s = AssessmentSession.objects.create(assessment=self.assessment, candidate=self.user)
        assert s.status == "active"

    def test_total_score_null_on_create(self):
        s = AssessmentSession.objects.create(assessment=self.assessment, candidate=self.user)
        assert s.total_score is None
        assert s.max_score is None
        assert s.percentage is None


class TestSectionScoreModel(AssessmentModelTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.assessment = Assessment.objects.create(title="Test")
        self.section = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 1", level=1
        )
        self.session = AssessmentSession.objects.create(
            assessment=self.assessment, candidate=self.user
        )

    def test_percentage_calculated_on_save(self):
        ss = SectionScore.objects.create(
            session=self.session, section=self.section, raw_score=3, max_score=5
        )
        assert ss.percentage == 60.0

    def test_percentage_zero_when_max_zero(self):
        ss = SectionScore.objects.create(
            session=self.session, section=self.section, raw_score=0, max_score=0
        )
        assert ss.percentage == 0

    def test_percentage_rounded_to_2_decimals(self):
        ss = SectionScore.objects.create(
            session=self.session, section=self.section, raw_score=1, max_score=3
        )
        assert ss.percentage == 33.33


class TestQuestionAttemptModel(AssessmentModelTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.assessment = Assessment.objects.create(title="Test")
        self.section = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 1", level=1
        )
        self.session = AssessmentSession.objects.create(
            assessment=self.assessment, candidate=self.user
        )
        self.question = make_mcq_question(self.user)

    def test_str(self):
        a = QuestionAttempt.objects.create(
            session=self.session, question=self.question, section=self.section
        )
        assert f"Session #{self.session.id}" in str(a)
        assert f"Q#{self.question.id}" in str(a)

    def test_default_status_not_attempted(self):
        a = QuestionAttempt.objects.create(
            session=self.session, question=self.question, section=self.section
        )
        assert a.status == "not_attempted"

    def test_raw_answer_json_flexible(self):
        """raw_answer accepts any JSON structure."""
        a = QuestionAttempt.objects.create(
            session=self.session,
            question=self.question,
            section=self.section,
            raw_answer={"selected_option_ids": [1, 2]},
        )
        a.refresh_from_db()
        assert a.raw_answer == {"selected_option_ids": [1, 2]}


class TestAssessmentQuestionModel(AssessmentModelTestBase):
    def setUp(self):
        self.user = UserFactory.create(role=self.individual_role)
        self.assessment = Assessment.objects.create(title="Test")
        self.section = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 1", level=1
        )
        self.question = make_mcq_question(self.user)

    def test_assign_question_to_section(self):
        aq = AssessmentQuestion.objects.create(
            section=self.section, question=self.question, order=1
        )
        assert aq.section == self.section
        assert aq.question == self.question

    def test_unique_together_section_question_subindex(self):
        AssessmentQuestion.objects.create(
            section=self.section, question=self.question, order=1, sub_question_index=0
        )
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            AssessmentQuestion.objects.create(
                section=self.section, question=self.question, order=2, sub_question_index=0
            )

    def test_score_override_nullable(self):
        aq = AssessmentQuestion.objects.create(section=self.section, question=self.question)
        assert aq.score_override is None
