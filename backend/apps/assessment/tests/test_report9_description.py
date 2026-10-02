"""Report 9 #75: the assessment Description and Instructions are rich text
(formatting + images) shown to candidates on the description page, so the
stored HTML is sanitised."""

from rest_framework import status
from rest_framework.test import APIClient

from apps.assessment.models import Assessment

from .factories import UserFactory, get_or_create_role
from .test_views import AssessmentViewTestBase, grant_assessment_perms

DIRTY = (
    '<p style="color: #ff0000">Read <em>carefully</em></p>'
    '<img src="https://cdn.example.com/diagram.png" onerror="alert(1)">'
    "<script>alert('x')</script>"
)


class TestAssessmentRichDescription(AssessmentViewTestBase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory.create(role=get_or_create_role("cj_admin", is_system=True))
        grant_assessment_perms(self.user)
        self.client.force_authenticate(user=self.user)

    def _assert_clean(self, html):
        assert "<script" not in html
        assert "onerror" not in html
        assert "<em>carefully</em>" in html
        assert "color:#ff0000" in html
        assert '<img src="https://cdn.example.com/diagram.png">' in html

    def test_create_sanitises_description_and_instructions(self):
        resp = self.client.post(
            "/api/assessments/",
            {"title": "Rich", "description": DIRTY, "instructions": DIRTY},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        a = Assessment.objects.get(id=resp.json()["data"]["id"])
        self._assert_clean(a.description)
        self._assert_clean(a.instructions)

    def test_update_sanitises_description_and_keeps_plain_text(self):
        a = Assessment.objects.create(title="Plain", created_by=self.user)
        resp = self.client.patch(
            f"/api/assessments/{a.id}/",
            {"description": DIRTY, "instructions": "Answer all questions.\nNo negative marks."},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        a.refresh_from_db()
        self._assert_clean(a.description)
        # Plain-text instructions written before the editor are left untouched.
        assert a.instructions == "Answer all questions.\nNo negative marks."

    def test_candidate_reads_description_of_published_assessment(self):
        a = Assessment.objects.create(
            title="Live",
            status="published",
            objective="Measure aptitude",
            description="<p>About this test</p>",
            instructions="<ol><li>Read</li></ol>",
            created_by=self.user,
        )
        candidate = UserFactory.create(role=get_or_create_role("individual", is_system=True))
        grant_assessment_perms(candidate, actions=("view",))
        client = APIClient()
        client.force_authenticate(user=candidate)
        data = client.get(f"/api/assessments/{a.id}/").json()["data"]
        assert data["objective"] == "Measure aptitude"
        assert data["description"] == "<p>About this test</p>"
        assert data["instructions"] == "<ol><li>Read</li></ol>"
