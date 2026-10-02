"""Report 9 #107: the CJ Admin approval panel lists modification requests.

The frontend reads this endpoint as a plain list in the {message, data}
envelope; pin that contract and confirm a psychometrician's delete request
on a published assessment shows up for CJ Admin and can be approved.
"""

from rest_framework import status
from rest_framework.test import APIClient

from apps.assessment.models import Assessment, AssessmentModificationRequest

from .factories import UserFactory, get_or_create_role
from .test_views import AssessmentViewTestBase, grant_assessment_perms


class ModificationRequestListTests(AssessmentViewTestBase):
    def setUp(self):
        self.admin = UserFactory.create(role=get_or_create_role("cj_admin", is_system=True))
        grant_assessment_perms(self.admin)
        self.author = UserFactory.create(role=get_or_create_role("psychometrician", is_system=True))
        grant_assessment_perms(self.author)
        self.assessment = Assessment.objects.create(
            title="Trial Testing Assessment", status="published", created_by=self.author
        )

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_delete_request_listed_for_admin_as_plain_list_and_approvable(self):
        author = self._client(self.author)
        resp = author.delete(
            f"/api/assessments/{self.assessment.id}/",
            {"reason": "No longer needed"},
            format="json",
        )
        assert resp.status_code in (200, 201, 202), resp.content
        assert AssessmentModificationRequest.objects.filter(
            assessment=self.assessment, action="delete", status="pending"
        ).exists()

        admin = self._client(self.admin)
        resp = admin.get("/api/assessment-modification-requests/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert [(r["assessment"], r["action"], r["status"]) for r in data] == [
            (self.assessment.id, "delete", "pending")
        ]

        resp = admin.post(
            f"/api/assessment-modification-requests/{data[0]['id']}/approve/", format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content
        assert not Assessment.objects.filter(id=self.assessment.id).exists()
