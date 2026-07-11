"""Tests for the Assessment API endpoints."""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
    QuestionAttempt,
)

from .factories import (
    UserFactory,
    get_or_create_role,
    make_mcq_question,
    make_rating_question,
)


class AssessmentViewTestBase(TestCase):
    """Ensure default roles exist so UserFactory can assign them."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        get_or_create_default_roles()


def grant_assessment_perms(user, actions=("view", "add", "change", "delete")):
    """Grant assessment module permissions to a user via their role.

    The user must already have a Role assigned (UserFactory assigns 'individual'
    by default). We attach ModuleRights to that role.
    """
    role = user.role
    if role is None:
        # Fallback: create a custom role for this user
        role = Role.objects.create(name=f"test_role_{user.id}", is_system=False)
        user.role = role
        user.save(update_fields=["role"])
    for action in actions:
        ModuleRight.objects.get_or_create(role=role, module="assessment", action=action)
    return role


class TestAssessmentCRUD(AssessmentViewTestBase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory.create(role=get_or_create_role("cj_admin", is_system=True))
        # cj_admin is a system role — give it assessment module rights
        grant_assessment_perms(self.user)
        self.client.force_authenticate(user=self.user)

    def test_create_assessment(self):
        resp = self.client.post(
            "/api/assessments/",
            {
                "title": "New Test",
                "objective": "Test objective",
                "description": "Test description",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["data"]["title"] == "New Test"
        assert resp.json()["data"]["status"] == "draft"

    def test_create_assessment_stores_duration_in_seconds(self):
        """total_duration_seconds is stored as-is (seconds) on the backend.

        The frontend converts minutes → seconds before sending. This test
        verifies the backend doesn't do any additional conversion.
        """
        resp = self.client.post(
            "/api/assessments/",
            {
                "title": "Timed Test",
                "total_duration_seconds": 900,  # 15 minutes in seconds
                "display_order": "STATIC",
                "timer_level": "assessment",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["data"]["total_duration_seconds"] == 900
        assert resp.json()["data"]["display_order"] == "STATIC"
        assert resp.json()["data"]["timer_level"] == "assessment"

    def test_update_assessment_duration(self):
        """PATCH can update total_duration_seconds."""
        a = Assessment.objects.create(title="Test", created_by=self.user)
        resp = self.client.patch(
            f"/api/assessments/{a.id}/",
            {"total_duration_seconds": 1800},  # 30 minutes
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["data"]["total_duration_seconds"] == 1800
        a.refresh_from_db()
        assert a.total_duration_seconds == 1800

    def test_list_assessments(self):
        Assessment.objects.create(title="A1", created_by=self.user)
        Assessment.objects.create(title="A2", created_by=self.user)
        resp = self.client.get("/api/assessments/")
        assert resp.status_code == status.HTTP_200_OK
        # Response may be paginated — look at results key OR data key
        data = resp.json()["data"]
        results = data.get("results", data) if isinstance(data, dict) else data
        assert len(results) >= 2

    def test_retrieve_assessment(self):
        a = Assessment.objects.create(title="Test 1", created_by=self.user)
        resp = self.client.get(f"/api/assessments/{a.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["data"]["title"] == "Test 1"

    def test_update_assessment_draft(self):
        a = Assessment.objects.create(title="Test 1", created_by=self.user)
        resp = self.client.patch(f"/api/assessments/{a.id}/", {"title": "Updated"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["data"]["title"] == "Updated"

    def test_cannot_update_published_assessment_non_admin(self):
        """Non-admin users cannot edit a published assessment (must archive first)."""
        # Switch to a non-admin role (corp_admin) to test the restriction.
        corp_admin = UserFactory.create(role=get_or_create_role("corp_admin", is_system=True))
        grant_assessment_perms(corp_admin)
        self.client.force_authenticate(user=corp_admin)
        a = Assessment.objects.create(title="Test 1", status="published", created_by=self.user)
        resp = self.client.patch(f"/api/assessments/{a.id}/", {"title": "Updated"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cj_admin_can_update_published_assessment(self):
        """cj_admin can override the publish-lock and edit any assessment."""
        a = Assessment.objects.create(title="Test 1", status="published", created_by=self.user)
        resp = self.client.patch(
            f"/api/assessments/{a.id}/", {"title": "Admin Updated"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        a.refresh_from_db()
        assert a.title == "Admin Updated"

    def test_delete_draft_assessment(self):
        a = Assessment.objects.create(title="Test 1", created_by=self.user)
        resp = self.client.delete(f"/api/assessments/{a.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not Assessment.objects.filter(id=a.id).exists()

    def test_cannot_delete_published_assessment_non_admin(self):
        """Non-admin users cannot delete a published assessment."""
        corp_admin = UserFactory.create(role=get_or_create_role("corp_admin", is_system=True))
        grant_assessment_perms(corp_admin)
        self.client.force_authenticate(user=corp_admin)
        a = Assessment.objects.create(title="Test 1", status="published", created_by=self.user)
        resp = self.client.delete(f"/api/assessments/{a.id}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cj_admin_can_delete_published_assessment(self):
        """cj_admin can override the publish-lock and delete any assessment."""
        a = Assessment.objects.create(title="Test 1", status="published", created_by=self.user)
        resp = self.client.delete(f"/api/assessments/{a.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not Assessment.objects.filter(id=a.id).exists()

    def test_publish_assessment(self):
        a = Assessment.objects.create(title="Test 1", status="draft", created_by=self.user)
        resp = self.client.post(f"/api/assessments/{a.id}/publish/")
        assert resp.status_code == status.HTTP_200_OK
        a.refresh_from_db()
        assert a.status == "published"

    def test_cannot_publish_non_draft(self):
        a = Assessment.objects.create(title="Test 1", status="published", created_by=self.user)
        resp = self.client.post(f"/api/assessments/{a.id}/publish/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestSectionCRUD(AssessmentViewTestBase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory.create(role=get_or_create_role("cj_admin", is_system=True))
        grant_assessment_perms(self.user)
        self.client.force_authenticate(user=self.user)
        self.assessment = Assessment.objects.create(title="Test", created_by=self.user)

    def test_create_section(self):
        resp = self.client.post(
            f"/api/assessments/{self.assessment.id}/sections/",
            {"title": "Section 1", "level": 1, "order": 1},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["data"]["title"] == "Section 1"

    def test_list_sections(self):
        AssessmentSection.objects.create(assessment=self.assessment, title="S1", level=1, order=1)
        AssessmentSection.objects.create(assessment=self.assessment, title="S2", level=1, order=2)
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/sections/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        results = data.get("results", data) if isinstance(data, dict) else data
        assert len(results) >= 2

    def test_section_includes_subsections(self):
        parent = AssessmentSection.objects.create(
            assessment=self.assessment, title="Parent", level=1, order=1
        )
        AssessmentSection.objects.create(
            assessment=self.assessment, parent=parent, title="Child", level=2, order=1
        )
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/")
        sections = resp.json()["data"]["sections"]
        assert len(sections) >= 1
        # Find parent
        parent_section = next(s for s in sections if s["title"] == "Parent")
        assert len(parent_section["subsections"]) == 1
        assert parent_section["subsections"][0]["title"] == "Child"

    def test_update_section_title(self):
        """PATCH /api/assessments/<aid>/sections/<id>/ updates the section."""
        section = AssessmentSection.objects.create(
            assessment=self.assessment, title="Original Title", level=1, order=1
        )
        resp = self.client.patch(
            f"/api/assessments/{self.assessment.id}/sections/{section.id}/",
            {"title": "Updated Title", "description": "New description"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["data"]["title"] == "Updated Title"
        assert resp.json()["data"]["description"] == "New description"
        section.refresh_from_db()
        assert section.title == "Updated Title"
        assert section.description == "New description"

    def test_update_section_response_envelope(self):
        """Section PATCH returns the {message, data} envelope (not bare DRF output)."""
        section = AssessmentSection.objects.create(
            assessment=self.assessment, title="S1", level=1, order=1
        )
        resp = self.client.patch(
            f"/api/assessments/{self.assessment.id}/sections/{section.id}/",
            {"title": "S1 updated"},
            format="json",
        )
        body = resp.json()
        assert "message" in body
        assert "data" in body
        assert body["message"] == "Section updated."

    def test_delete_section(self):
        """DELETE /api/assessments/<aid>/sections/<id>/ removes the section."""
        section = AssessmentSection.objects.create(
            assessment=self.assessment, title="To Delete", level=1, order=1
        )
        resp = self.client.delete(f"/api/assessments/{self.assessment.id}/sections/{section.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["message"] == "Section deleted."
        assert not AssessmentSection.objects.filter(id=section.id).exists()

    def test_delete_section_cascades_to_subsections(self):
        """Deleting a parent section cascades to its sub-sections."""
        parent = AssessmentSection.objects.create(
            assessment=self.assessment, title="Parent", level=1, order=1
        )
        child = AssessmentSection.objects.create(
            assessment=self.assessment, parent=parent, title="Child", level=2, order=1
        )
        resp = self.client.delete(f"/api/assessments/{self.assessment.id}/sections/{parent.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not AssessmentSection.objects.filter(id=parent.id).exists()
        assert not AssessmentSection.objects.filter(id=child.id).exists()

    def test_delete_section_cascades_to_assigned_questions(self):
        """Deleting a section cascades to its AssessmentQuestion rows."""
        from apps.assessment.tests.factories import make_mcq_question

        section = AssessmentSection.objects.create(
            assessment=self.assessment, title="With Questions", level=1, order=1
        )
        question = make_mcq_question(self.user)
        aq = AssessmentQuestion.objects.create(section=section, question=question, order=1)
        resp = self.client.delete(f"/api/assessments/{self.assessment.id}/sections/{section.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not AssessmentQuestion.objects.filter(id=aq.id).exists()


class TestQuestionAssignment(AssessmentViewTestBase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory.create(role=get_or_create_role("cj_admin", is_system=True))
        grant_assessment_perms(self.user)
        self.client.force_authenticate(user=self.user)
        self.assessment = Assessment.objects.create(title="Test", created_by=self.user)
        self.section = AssessmentSection.objects.create(
            assessment=self.assessment, title="S1", level=1, order=1
        )
        self.question = make_mcq_question(self.user)

    def test_assign_question_to_section(self):
        resp = self.client.post(
            f"/api/assessments/{self.assessment.id}/sections/{self.section.id}/questions/",
            {"question": self.question.id, "order": 1},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["data"]["question"] == self.question.id
        # Should include question_detail
        assert "question_detail" in resp.json()["data"]

    def test_list_assigned_questions(self):
        AssessmentQuestion.objects.create(section=self.section, question=self.question, order=1)
        resp = self.client.get(
            f"/api/assessments/{self.assessment.id}/sections/{self.section.id}/questions/"
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        results = data.get("results", data) if isinstance(data, dict) else data
        assert len(results) == 1

    def test_remove_question_from_section(self):
        aq = AssessmentQuestion.objects.create(
            section=self.section, question=self.question, order=1
        )
        resp = self.client.delete(
            f"/api/assessments/{self.assessment.id}/sections/{self.section.id}/questions/{aq.id}/"
        )
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)
        assert not AssessmentQuestion.objects.filter(id=aq.id).exists()


class TestSessionFlow(AssessmentViewTestBase):
    """End-to-end: start session → answer → submit → see scores."""

    def setUp(self):
        self.client = APIClient()
        # Admin/author user (creates the assessment)
        self.admin = UserFactory.create(role=get_or_create_role("cj_admin", is_system=True))
        grant_assessment_perms(self.admin)
        # Candidate user (takes the assessment)
        self.candidate = UserFactory.create(role=get_or_create_role("individual", is_system=True))
        grant_assessment_perms(self.candidate, actions=("view",))

        # Create published assessment with one section, two questions
        self.assessment = Assessment.objects.create(
            title="Maths Test",
            status="published",
            created_by=self.admin,
            total_duration_seconds=600,
        )
        self.section = AssessmentSection.objects.create(
            assessment=self.assessment, title="Section 1", level=1, order=1
        )
        self.q1 = make_mcq_question(self.admin)  # Binary scoring
        self.q2 = make_rating_question(self.admin)  # 5-point rating
        AssessmentQuestion.objects.create(section=self.section, question=self.q1, order=1)
        AssessmentQuestion.objects.create(section=self.section, question=self.q2, order=2)

    def test_start_session_creates_attempts(self):
        self.client.force_authenticate(user=self.candidate)
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        assert resp.status_code == status.HTTP_201_CREATED
        session_id = resp.json()["data"]["id"]
        # Should pre-create 2 QuestionAttempt records
        session = AssessmentSession.objects.get(id=session_id)
        assert session.question_attempts.count() == 2
        # And expose total_duration_seconds from assessment
        assert resp.json()["data"]["total_duration_seconds"] == 600

    def test_cannot_start_session_for_draft_assessment(self):
        self.assessment.status = "draft"
        self.assessment.save()
        self.client.force_authenticate(user=self.candidate)
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_resuming_active_session_returns_same_session(self):
        self.client.force_authenticate(user=self.candidate)
        resp1 = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        resp2 = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        assert resp1.json()["data"]["id"] == resp2.json()["data"]["id"]

    def test_get_session_questions(self):
        self.client.force_authenticate(user=self.candidate)
        start = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        sid = start.json()["data"]["id"]
        resp = self.client.get(f"/api/assessments/sessions/{sid}/questions/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert len(data) == 2
        # Each item should have full question_detail with options
        first = data[0]
        assert "question_detail" in first
        assert "options" in first["question_detail"]

    def test_submit_answer(self):
        self.client.force_authenticate(user=self.candidate)
        start = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        sid = start.json()["data"]["id"]
        # Find the MCQ attempt
        attempt = QuestionAttempt.objects.get(session_id=sid, question=self.q1)
        correct_opt = self.q1.options.filter(is_correct=True).first()
        resp = self.client.post(
            f"/api/assessments/sessions/{sid}/answer/",
            {"question_id": self.q1.id, "raw_answer": {"selected_option_ids": [correct_opt.id]}},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        attempt.refresh_from_db()
        assert attempt.status == "attempted"
        assert attempt.raw_answer == {"selected_option_ids": [correct_opt.id]}

    def test_submit_session_calculates_scores(self):
        self.client.force_authenticate(user=self.candidate)
        start = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        sid = start.json()["data"]["id"]
        # Answer both questions correctly
        correct_opt = self.q1.options.filter(is_correct=True).first()
        self.client.post(
            f"/api/assessments/sessions/{sid}/answer/",
            {"question_id": self.q1.id, "raw_answer": {"selected_option_ids": [correct_opt.id]}},
            format="json",
        )
        self.client.post(
            f"/api/assessments/sessions/{sid}/answer/",
            {"question_id": self.q2.id, "raw_answer": {"rating": 1}},  # forward → score=5
            format="json",
        )

        resp = self.client.post(f"/api/assessments/sessions/{sid}/submit/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert data["session"]["status"] == "completed"
        assert data["session"]["total_score"] == 6.0  # 1 (binary) + 5 (rating)
        assert data["session"]["max_score"] == 6.0
        # Section scores should be returned
        assert len(data["section_scores"]) == 1
        assert data["section_scores"][0]["raw_score"] == 6.0

    def test_suspend_and_resume_session(self):
        self.client.force_authenticate(user=self.candidate)
        start = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        sid = start.json()["data"]["id"]

        # Suspend
        suspend_resp = self.client.post(f"/api/assessments/sessions/{sid}/suspend/")
        assert suspend_resp.status_code == status.HTTP_200_OK
        assert suspend_resp.json()["data"]["status"] == "suspended"

        # Resume (start_session should reactivate it)
        resume_resp = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        assert resume_resp.status_code == status.HTTP_200_OK
        assert resume_resp.json()["data"]["status"] == "active"
        assert resume_resp.json()["data"]["id"] == sid

    def test_cannot_submit_inactive_session(self):
        self.client.force_authenticate(user=self.candidate)
        start = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        sid = start.json()["data"]["id"]
        # Suspend first
        self.client.post(f"/api/assessments/sessions/{sid}/suspend/")
        # Now try to submit — should fail
        resp = self.client.post(f"/api/assessments/sessions/{sid}/submit/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_get_section_scores_after_completion(self):
        self.client.force_authenticate(user=self.candidate)
        start = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        sid = start.json()["data"]["id"]
        # Answer correctly
        correct_opt = self.q1.options.filter(is_correct=True).first()
        self.client.post(
            f"/api/assessments/sessions/{sid}/answer/",
            {"question_id": self.q1.id, "raw_answer": {"selected_option_ids": [correct_opt.id]}},
            format="json",
        )
        # Submit
        self.client.post(f"/api/assessments/sessions/{sid}/submit/")

        # Now fetch section scores
        resp = self.client.get(f"/api/assessments/sessions/{sid}/section_scores/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["section_title"] == "Section 1"
        assert data[0]["raw_score"] == 1.0  # only q1 answered

    def test_candidate_only_sees_own_sessions(self):
        # Create session as candidate
        self.client.force_authenticate(user=self.candidate)
        start = self.client.post(f"/api/assessments/{self.assessment.id}/start_session/")
        sid = start.json()["data"]["id"]

        # Another candidate should NOT see this session
        other = UserFactory.create(role=get_or_create_role("individual", is_system=True))
        grant_assessment_perms(other, actions=("view",))
        self.client.force_authenticate(user=other)
        resp = self.client.get(f"/api/assessments/sessions/{sid}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestAssessmentTypeEnforcement(AssessmentViewTestBase):
    """Verify that normal and psychometric questions cannot be mixed in one assessment.

    Per SRS 03_assessment_configuration.json §4.1 vs §4.2, an assessment must
    contain either normal questions (MCQ/FITB/Match/Grid/Hotspot) OR psychometric
    questions (Rating/Rank/Rank-then-Rate/Forced-Choice) — never both.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory.create(role=get_or_create_role("cj_admin", is_system=True))
        grant_assessment_perms(self.user)
        self.client.force_authenticate(user=self.user)

        # Two assessments — one normal, one psychometric
        self.normal_assessment = Assessment.objects.create(
            title="Normal Test",
            assessment_type="normal",
            created_by=self.user,
        )
        self.psychometric_assessment = Assessment.objects.create(
            title="Psychometric Test",
            assessment_type="psychometric",
            created_by=self.user,
        )
        self.normal_section = AssessmentSection.objects.create(
            assessment=self.normal_assessment, title="Normal Section", level=1, order=1
        )
        self.psychometric_section = AssessmentSection.objects.create(
            assessment=self.psychometric_assessment,
            title="Psychometric Section",
            level=1,
            order=1,
        )

        # Normal question (MCQ) and psychometric question (Rating)
        self.normal_question = make_mcq_question(self.user)
        self.psychometric_question = make_rating_question(self.user)

    def test_normal_question_can_attach_to_normal_assessment(self):
        """A normal question (MCQ) can be attached to a normal assessment."""
        resp = self.client.post(
            f"/api/assessments/{self.normal_assessment.id}/sections/"
            f"{self.normal_section.id}/questions/",
            {"question": self.normal_question.id, "order": 1},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_psychometric_question_can_attach_to_psychometric_assessment(self):
        """A psychometric question (Rating) can be attached to a psychometric assessment."""
        resp = self.client.post(
            f"/api/assessments/{self.psychometric_assessment.id}/sections/"
            f"{self.psychometric_section.id}/questions/",
            {"question": self.psychometric_question.id, "order": 1},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_psychometric_question_rejected_for_normal_assessment(self):
        """A psychometric question (Rating) cannot be attached to a normal assessment."""
        resp = self.client.post(
            f"/api/assessments/{self.normal_assessment.id}/sections/"
            f"{self.normal_section.id}/questions/",
            {"question": self.psychometric_question.id, "order": 1},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        body = resp.json()
        assert body["error"]["code"] == "question_category_mismatch"
        assert body["error"]["details"]["assessment_type"] == "normal"
        assert body["error"]["details"]["question_category"] == "psychometric"
        # Verify the question was NOT assigned
        assert not AssessmentQuestion.objects.filter(
            section=self.normal_section, question=self.psychometric_question
        ).exists()

    def test_normal_question_rejected_for_psychometric_assessment(self):
        """A normal question (MCQ) cannot be attached to a psychometric assessment."""
        resp = self.client.post(
            f"/api/assessments/{self.psychometric_assessment.id}/sections/"
            f"{self.psychometric_section.id}/questions/",
            {"question": self.normal_question.id, "order": 1},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        body = resp.json()
        assert body["error"]["code"] == "question_category_mismatch"
        assert body["error"]["details"]["assessment_type"] == "psychometric"
        assert body["error"]["details"]["question_category"] == "normal"
        # Verify the question was NOT assigned
        assert not AssessmentQuestion.objects.filter(
            section=self.psychometric_section, question=self.normal_question
        ).exists()

    def test_default_assessment_type_is_normal(self):
        """New assessments default to assessment_type='normal'."""
        a = Assessment.objects.create(title="Default Test", created_by=self.user)
        assert a.assessment_type == "normal"

    def test_question_category_property_is_correct(self):
        """The Question.is_psychometric and Question.question_category properties work."""
        assert self.normal_question.is_psychometric is False
        assert self.normal_question.question_category == "normal"
        assert self.psychometric_question.is_psychometric is True
        assert self.psychometric_question.question_category == "psychometric"

    def test_assessment_type_exposed_in_api(self):
        """The assessment serializer exposes assessment_type and assessment_type_label."""
        resp = self.client.get(f"/api/assessments/{self.psychometric_assessment.id}/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert data["assessment_type"] == "psychometric"
        assert "psychometric" in data["assessment_type_label"].lower()
