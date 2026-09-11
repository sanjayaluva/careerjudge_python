"""Tests for the D5 dossier "medium" gap items implemented for
career_profiling:

  5. Band definition guards (SRS §4.1.1): min 2 / max 10 bands per variable,
     band range within 0-100, no overlapping ranges, at least 2 variables
     selected (enforced at publish time).
  6. Criterion band dropdown: criterion_band_code is validated against the
     band codes actually defined for that variable.
  7. Criterion template upload (SRS §4.1.4): CSV upload creates/updates
     MappingCriterion rows.
"""

import csv
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.assessment.models import Assessment, AssessmentSection
from apps.career_profiling.models import (
    Band,
    BandDefinition,
    MappingCriterion,
    ProfilingSolution,
    SelectedAssessment,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def psychometrician_user(db, roles):
    role = roles["psychometrician"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="career_profiling", action=action)
    return UserFactory(role=role, email="psy-cp-dossier@test.com")


@pytest.fixture
def psy_client(db, psychometrician_user):
    c = APIClient()
    refresh = RefreshToken.for_user(psychometrician_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


def _make_solution(created_by):
    return ProfilingSolution.objects.create(title="S", status="draft", created_by=created_by)


def _make_selected_assessment(solution, label="A1"):
    assessment = Assessment.objects.create(title=f"Assessment-{label}", status="published")
    return SelectedAssessment.objects.create(solution=solution, assessment=assessment, label=label)


def _make_band_definition(sa, title):
    section = AssessmentSection.objects.create(assessment=sa.assessment, title=title, level=1)
    return BandDefinition.objects.create(selected_assessment=sa, section=section)


# ---------------------------------------------------------------------------
# 5. Band definition guards
# ---------------------------------------------------------------------------


class TestBandGuards:
    def test_range_must_be_within_0_100(self, psy_client, psychometrician_user):
        solution = _make_solution(psychometrician_user)
        sa = _make_selected_assessment(solution)
        bd = _make_band_definition(sa, "V1")

        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/band_rows/",
            {
                "band_definition": bd.id,
                "band_number": 1,
                "range_min": -5,
                "range_max": 20,
                "band_code": "X1",
            },
            format="json",
        )
        assert resp.status_code == 400

        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/band_rows/",
            {
                "band_definition": bd.id,
                "band_number": 1,
                "range_min": 80,
                "range_max": 120,
                "band_code": "X2",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_range_min_must_be_less_than_max(self, psy_client, psychometrician_user):
        solution = _make_solution(psychometrician_user)
        sa = _make_selected_assessment(solution)
        bd = _make_band_definition(sa, "V1")

        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/band_rows/",
            {
                "band_definition": bd.id,
                "band_number": 1,
                "range_min": 50,
                "range_max": 50,
                "band_code": "X1",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_overlapping_bands_rejected(self, psy_client, psychometrician_user):
        solution = _make_solution(psychometrician_user)
        sa = _make_selected_assessment(solution)
        bd = _make_band_definition(sa, "V1")
        Band.objects.create(
            band_definition=bd, band_number=1, range_min=0, range_max=50, band_code="L"
        )

        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/band_rows/",
            {
                "band_definition": bd.id,
                "band_number": 2,
                "range_min": 40,
                "range_max": 100,
                "band_code": "H",
            },
            format="json",
        )
        assert resp.status_code == 400

        # Non-overlapping range is accepted
        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/band_rows/",
            {
                "band_definition": bd.id,
                "band_number": 2,
                "range_min": 50.01,
                "range_max": 100,
                "band_code": "H",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content

    def test_max_10_bands_per_variable(self, psy_client, psychometrician_user):
        solution = _make_solution(psychometrician_user)
        sa = _make_selected_assessment(solution)
        bd = _make_band_definition(sa, "V1")
        for i in range(10):
            Band.objects.create(
                band_definition=bd,
                band_number=i + 1,
                range_min=i * 10,
                range_max=(i + 1) * 10 - 0.01,
                band_code=f"B{i}",
            )

        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/band_rows/",
            {
                "band_definition": bd.id,
                "band_number": 11,
                "range_min": 99.99,
                "range_max": 100,
                "band_code": "B11",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_publish_rejects_fewer_than_2_variables(self, psy_client, psychometrician_user):
        solution = _make_solution(psychometrician_user)
        sa1 = _make_selected_assessment(solution, "A1")
        sa2 = _make_selected_assessment(solution, "A2")
        # Only 1 variable (band_definition) on sa1 — fails "at least 2 variables"
        bd = _make_band_definition(sa1, "V1")
        Band.objects.create(
            band_definition=bd, band_number=1, range_min=0, range_max=50, band_code="L"
        )
        Band.objects.create(
            band_definition=bd, band_number=2, range_min=50, range_max=100, band_code="H"
        )
        bd2a = _make_band_definition(sa2, "V1")
        bd2b = _make_band_definition(sa2, "V2")
        for bd_ in (bd2a, bd2b):
            Band.objects.create(
                band_definition=bd_, band_number=1, range_min=0, range_max=50, band_code="L"
            )
            Band.objects.create(
                band_definition=bd_, band_number=2, range_min=50, range_max=100, band_code="H"
            )

        resp = psy_client.post(f"/api/career-profiling/solutions/{solution.id}/publish/")
        assert resp.status_code == 400
        assert "variables" in resp.json()["error"]["message"]

    def test_publish_rejects_fewer_than_2_bands_per_variable(
        self, psy_client, psychometrician_user
    ):
        solution = _make_solution(psychometrician_user)
        sa1 = _make_selected_assessment(solution, "A1")
        sa2 = _make_selected_assessment(solution, "A2")
        bd1 = _make_band_definition(sa1, "V1")
        bd2 = _make_band_definition(sa1, "V2")
        Band.objects.create(
            band_definition=bd1, band_number=1, range_min=0, range_max=100, band_code="ONLY"
        )
        Band.objects.create(
            band_definition=bd2, band_number=1, range_min=0, range_max=50, band_code="L"
        )
        Band.objects.create(
            band_definition=bd2, band_number=2, range_min=50, range_max=100, band_code="H"
        )
        bd3a = _make_band_definition(sa2, "V1")
        bd3b = _make_band_definition(sa2, "V2")
        for bd_ in (bd3a, bd3b):
            Band.objects.create(
                band_definition=bd_, band_number=1, range_min=0, range_max=50, band_code="L"
            )
            Band.objects.create(
                band_definition=bd_, band_number=2, range_min=50, range_max=100, band_code="H"
            )

        resp = psy_client.post(f"/api/career-profiling/solutions/{solution.id}/publish/")
        assert resp.status_code == 400
        assert "at least 2 bands" in resp.json()["error"]["message"]

    def test_publish_succeeds_with_valid_band_definitions(self, psy_client, psychometrician_user):
        solution = _make_solution(psychometrician_user)
        for label in ("A1", "A2"):
            sa = _make_selected_assessment(solution, label)
            for vtitle in ("V1", "V2"):
                bd = _make_band_definition(sa, vtitle)
                Band.objects.create(
                    band_definition=bd, band_number=1, range_min=0, range_max=50, band_code="L"
                )
                Band.objects.create(
                    band_definition=bd, band_number=2, range_min=50, range_max=100, band_code="H"
                )

        resp = psy_client.post(f"/api/career-profiling/solutions/{solution.id}/publish/")
        assert resp.status_code == 200, resp.content


# ---------------------------------------------------------------------------
# 6. Criterion band dropdown (validated against defined band codes)
# ---------------------------------------------------------------------------


class TestCriterionBandValidation:
    def _solution_with_band(self, created_by):
        solution = _make_solution(created_by)
        sa = _make_selected_assessment(solution)
        bd = _make_band_definition(sa, "V1")
        Band.objects.create(
            band_definition=bd, band_number=1, range_min=0, range_max=50, band_code="L"
        )
        Band.objects.create(
            band_definition=bd, band_number=2, range_min=50, range_max=100, band_code="H"
        )
        return solution, bd

    def test_valid_band_code_accepted(self, psy_client, psychometrician_user):
        solution, bd = self._solution_with_band(psychometrician_user)
        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/criteria/",
            {
                "career_title": "Programmer",
                "section": bd.section_id,
                "criterion_band_code": "H",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content

    def test_invalid_band_code_rejected(self, psy_client, psychometrician_user):
        solution, bd = self._solution_with_band(psychometrician_user)
        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/criteria/",
            {
                "career_title": "Programmer",
                "section": bd.section_id,
                "criterion_band_code": "NOT_A_BAND",
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "criterion_band_code" in resp.json()["error"]["details"]

    def test_no_bands_defined_for_section_rejected(self, psy_client, psychometrician_user):
        solution = _make_solution(psychometrician_user)
        sa = _make_selected_assessment(solution)
        bd = _make_band_definition(sa, "Unbanded")  # no Band rows created

        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/criteria/",
            {
                "career_title": "Programmer",
                "section": bd.section_id,
                "criterion_band_code": "ANY",
            },
            format="json",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 7. Criterion template upload
# ---------------------------------------------------------------------------


class TestCriterionTemplateUpload:
    def _solution_with_two_variables(self, created_by):
        solution = _make_solution(created_by)
        sa = _make_selected_assessment(solution)
        bd1 = _make_band_definition(sa, "Analytical Reasoning")
        bd2 = _make_band_definition(sa, "Logical Reasoning")
        for bd, codes in ((bd1, ["ANL1", "ANH1"]), (bd2, ["LRL1", "LRH1"])):
            Band.objects.create(
                band_definition=bd, band_number=1, range_min=0, range_max=50, band_code=codes[0]
            )
            Band.objects.create(
                band_definition=bd, band_number=2, range_min=50, range_max=100, band_code=codes[1]
            )
        return solution, bd1, bd2

    def test_template_download_has_variable_columns(self, psy_client, psychometrician_user):
        solution, bd1, bd2 = self._solution_with_two_variables(psychometrician_user)
        resp = psy_client.get(f"/api/career-profiling/solutions/{solution.id}/criteria-upload/")
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/csv")
        rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))
        header = rows[0]
        assert "Career Title" in header
        assert "Analytical Reasoning: Band Code" in header
        assert "Logical Reasoning: Rank Order" in header

    def test_upload_creates_mapping_criteria(self, psy_client, psychometrician_user):
        solution, bd1, bd2 = self._solution_with_two_variables(psychometrician_user)
        csv_content = (
            "Career Stream,Career Title,Career Description,Career Code,"
            "Analytical Reasoning: Band Code,Analytical Reasoning: Rank Order,"
            "Logical Reasoning: Band Code,Logical Reasoning: Rank Order\n"
            "IT Sector,Computer Programmer,Writes code,ITCP,ANH1,2,LRL1,\n"
            "IT Sector,Database Administrator,Manages DBs,ITDA,ANL1,0,LRH1,1\n"
        )
        file = SimpleUploadedFile(
            "criteria.csv", csv_content.encode("utf-8"), content_type="text/csv"
        )
        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/criteria-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()["data"]
        assert data["created_count"] == 4  # 2 careers x 2 variables
        assert data["error_count"] == 0

        criteria = MappingCriterion.objects.filter(
            solution=solution, career_title="Computer Programmer"
        )
        assert criteria.count() == 2
        analytical = criteria.get(section=bd1.section)
        assert analytical.criterion_band_code == "ANH1"
        assert analytical.rank_order == 2
        logical = criteria.get(section=bd2.section)
        assert logical.criterion_band_code == "LRL1"
        assert logical.rank_order is None  # empty column -> no rank

        dba = MappingCriterion.objects.filter(
            solution=solution, career_title="Database Administrator"
        )
        assert dba.get(section=bd1.section).rank_order is None  # "0" -> no rank
        assert dba.get(section=bd2.section).rank_order == 1

    def test_upload_is_idempotent_on_reupload(self, psy_client, psychometrician_user):
        solution, bd1, bd2 = self._solution_with_two_variables(psychometrician_user)
        csv_content = (
            "Career Stream,Career Title,Career Description,Career Code,"
            "Analytical Reasoning: Band Code,Analytical Reasoning: Rank Order,"
            "Logical Reasoning: Band Code,Logical Reasoning: Rank Order\n"
            "IT Sector,Computer Programmer,Writes code,ITCP,ANH1,,LRL1,\n"
        )
        for i in range(2):
            file = SimpleUploadedFile(
                f"criteria{i}.csv", csv_content.encode("utf-8"), content_type="text/csv"
            )
            resp = psy_client.post(
                f"/api/career-profiling/solutions/{solution.id}/criteria-upload/",
                {"file": file},
                format="multipart",
            )
            assert resp.status_code == 200, resp.content

        assert (
            MappingCriterion.objects.filter(
                solution=solution, career_title="Computer Programmer"
            ).count()
            == 2
        )

    def test_upload_reports_invalid_band_code_without_failing_whole_request(
        self, psy_client, psychometrician_user
    ):
        solution, bd1, bd2 = self._solution_with_two_variables(psychometrician_user)
        csv_content = (
            "Career Stream,Career Title,Career Description,Career Code,"
            "Analytical Reasoning: Band Code,Analytical Reasoning: Rank Order,"
            "Logical Reasoning: Band Code,Logical Reasoning: Rank Order\n"
            "IT Sector,Bad Row,desc,ITBR,NOT_REAL,,LRL1,\n"
        )
        file = SimpleUploadedFile(
            "criteria.csv", csv_content.encode("utf-8"), content_type="text/csv"
        )
        resp = psy_client.post(
            f"/api/career-profiling/solutions/{solution.id}/criteria-upload/",
            {"file": file},
            format="multipart",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()["data"]
        assert data["error_count"] == 1
        assert data["created_count"] == 1  # the valid Logical Reasoning row still created
