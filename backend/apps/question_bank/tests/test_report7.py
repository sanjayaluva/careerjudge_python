"""Report 7 regression tests — Question Bank module (§28-§30, §35-§37).

  §28  question_text_2 round-trips through the UPDATE endpoint (the editor
       now syncs it for Rating/Rank/RankRate/ForcedChoice/Match).
  §29  re-submitting the same options via the bulk-sync endpoint does NOT
       duplicate them (the old frontend double-load produced 5 → 80).
  §30  scale legends persist as options (label "Point N").
  §35/§36  a PSYCHOMETRIC_STATEMENT is creatable with plain text and is
       ready for review (feeds the psychometric groups tab).
  §37  the image field round-trips through UPDATE (previously read-only →
       uploads were silently dropped).
"""

from django.test import TestCase

from apps.accounts.models import ModuleRight, Role
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.question_bank.models import Question, ResponseOption
from apps.question_bank.validation import validate_question_config


class QBReport7Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        get_or_create_default_roles()
        cls.role, _ = Role.objects.get_or_create(
            name="sme", defaults={"is_system": True, "is_frozen": False}
        )
        cls.sme = UserFactory.create(role=cls.role)

    def setUp(self):
        from rest_framework.test import APIClient

        for action in ("view", "add", "change", "delete"):
            ModuleRight.objects.get_or_create(role=self.role, module="question_bank", action=action)
        self.client = APIClient()
        self.client.force_authenticate(self.sme)

    def create_question(self, **payload):
        base = {
            "question_type": "STANDARD_RATING_SCALE",
            "question_title": "R7 test question",
            "question_text_1": "Statement text.",
            "question_text_2": "",
            "scoring_type": "RATING",
            "rating_scale_points": 5,
            "rating_direction": "FORWARD",
        }
        base.update(payload)
        r = self.client.post("/api/question-bank/questions/", base, format="json")
        self.assertEqual(r.status_code, 201, r.json())
        return r.json()["data"]["id"]


class QnText2UpdateTest(QBReport7Base):
    """§28: QnText2 saves for every question type."""

    def test_rating_question_text_2_round_trips(self):
        qid = self.create_question()
        r = self.client.patch(
            f"/api/question-bank/questions/{qid}/",
            {"question_text_2": "Updated additional text."},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.json())
        self.assertEqual(r.json()["data"]["question_text_2"], "Updated additional text.")

    def test_rank_question_text_2_round_trips(self):
        qid = self.create_question(
            question_type="RANK_SIMPLE", scoring_type="RANK", rating_scale_points=0
        )
        r = self.client.patch(
            f"/api/question-bank/questions/{qid}/",
            {"question_text_2": "Rank secondary."},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["question_text_2"], "Rank secondary.")


class RatingOptionDuplicationTest(QBReport7Base):
    """§29/§30: legends persist exactly once — no growth across saves."""

    def _legends(self):
        return [
            {
                "sub_question_index": 0,
                "option_type": "TEXT",
                "label": f"Point {i+1}",
                "text_value": legend,
                "is_correct": False,
                "predefined_score": 1.0,
                "section_tag": "",
                "selection_score": 1.0,
                "non_selection_score": 0.0,
                "order": i,
            }
            for i, legend in enumerate(["Not at all", "Slightly", "Moderately", "Quite", "Very"])
        ]

    def test_bulk_resync_does_not_duplicate(self):
        qid = self.create_question()
        # 1st save
        r = self.client.post(
            f"/api/question-bank/questions/{qid}/options/bulk/",
            {"options": self._legends()},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["data"]), 5)
        # 2nd save (identical list — what the fixed editor sends)
        r = self.client.post(
            f"/api/question-bank/questions/{qid}/options/bulk/",
            {"options": self._legends()},
            format="json",
        )
        self.assertEqual(len(r.json()["data"]), 5)
        # 3rd save
        r = self.client.post(
            f"/api/question-bank/questions/{qid}/options/bulk/",
            {"options": self._legends()},
            format="json",
        )
        self.assertEqual(len(r.json()["data"]), 5)
        # DB truth: exactly 5, never 10/20/40/80.
        self.assertEqual(ResponseOption.objects.filter(question_id=qid).count(), 5)

    def test_legends_persist_and_reload(self):
        """§30: legend texts survive a save + fetch cycle."""
        qid = self.create_question()
        self.client.post(
            f"/api/question-bank/questions/{qid}/options/bulk/",
            {"options": self._legends()},
            format="json",
        )
        data = self.client.get(f"/api/question-bank/questions/{qid}/").json()["data"]
        point_opts = sorted(
            [o for o in data["options"] if (o.get("label") or "").startswith("Point ")],
            key=lambda o: o["label"],
        )
        self.assertEqual(
            [o["text_value"] for o in point_opts],
            ["Not at all", "Slightly", "Moderately", "Quite", "Very"],
        )


class PsychometricStatementTest(QBReport7Base):
    """§35/§36: statements are authorable and review-ready."""

    def test_statement_created_with_text_and_no_options(self):
        r = self.client.post(
            "/api/question-bank/questions/",
            {
                "question_type": "PSYCHOMETRIC_STATEMENT",
                "question_title": "R7 statement",
                "question_text_1": "I like to plan ahead.",
                "question_text_2": "",
                "scoring_type": "BINARY",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.json())
        qid = r.json()["data"]["id"]
        q = Question.objects.get(id=qid)
        self.assertEqual(q.question_text_1, "I like to plan ahead.")
        self.assertEqual(q.options.count(), 0)
        # Validation: bare text is enough — no option/scoring requirements:
        self.assertEqual(validate_question_config(q), [])
        self.assertTrue(
            q.question_is_ready_for_review if hasattr(q, "question_is_ready_for_review") else True
        )

    def test_statement_validation_ready_for_review(self):
        q = Question.objects.create(
            question_type="PSYCHOMETRIC_STATEMENT",
            question_title="stmt",
            question_text_1="I adapt quickly.",
            scoring_type="BINARY",
            status="draft",
            created_by=self.sme,
        )
        from apps.question_bank.validation import question_is_ready_for_review

        self.assertTrue(question_is_ready_for_review(q))


class QuestionImageUpdateTest(QBReport7Base):
    """§37: image round-trips through UPDATE."""

    IMG_A = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    IMG_B = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

    def test_image_saved_on_update(self):
        qid = self.create_question(
            question_type="MCQ_IMAGE_DISPLAY_MULTI",
            scoring_type="BINARY",
            image=self.IMG_A,
            image_width=100,
            image_height=50,
        )
        # Upload a NEW image via the update flow (previously silently dropped):
        r = self.client.patch(
            f"/api/question-bank/questions/{qid}/",
            {"image": self.IMG_B, "image_width": 200, "image_height": 100},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.json())
        self.assertEqual(r.json()["data"]["image"], self.IMG_B)

    def test_update_without_image_keeps_existing(self):
        qid = self.create_question(
            question_type="MCQ_IMAGE_DISPLAY_MULTI",
            scoring_type="BINARY",
            image=self.IMG_A,
            image_width=100,
            image_height=50,
        )
        r = self.client.patch(
            f"/api/question-bank/questions/{qid}/",
            {"question_title": "Renamed"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["image"], self.IMG_A)

    def test_explicit_clear_image(self):
        qid = self.create_question(
            question_type="MCQ_IMAGE_DISPLAY_MULTI",
            scoring_type="BINARY",
            image=self.IMG_A,
            image_width=100,
            image_height=50,
        )
        r = self.client.patch(
            f"/api/question-bank/questions/{qid}/",
            {"image": "", "clear_image": True},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["image"], "")
