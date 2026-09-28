"""Report 7 regression tests (System Testing & Review Report 7, 26-09-2026).

One test class per issue group, mirroring the client's reported scenarios:

  §1-5/§9/§10/§18/§19   — display order, resume, counts
  §7/§8                 — per-level RANDOM cascade
  §11                   — timer set at only ONE level
  §12/§34               — section/question assignment order
  §21                   — section timer context for the player
  §22                   — 1f combined sub-question score
  §24-§26               — FITB multi-field + flash recall scoring
  §27                   — multi-answer MCQ 1/2 semantics
  §28-§30               — (question_bank tests module)

Run: python manage.py test apps.assessment.tests.test_report7
"""

from django.test import TestCase

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
    QuestionAttempt,
)
from apps.assessment.ordering import compute_delivery_order, section_display_path
from apps.assessment.scoring import calculate_session_scores, score_question
from apps.question_bank.models import CorrectAnswer, FlashItem, ResponseOption

from .factories import UserFactory, _make_question, get_or_create_role


class Report7Base(TestCase):
    """Shared setup: roles + users."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        get_or_create_default_roles()
        cls.admin = UserFactory.create(role=get_or_create_role("cj_admin", is_system=True))
        cls.candidate = UserFactory.create(role=get_or_create_role("individual", is_system=True))

    def _granted_admin_client(self):
        """cj_admin + assessment + question_bank module rights (mirrors
        the existing view tests' permission grant helper)."""
        from rest_framework.test import APIClient

        for module in ("assessment", "question_bank"):
            for action in ("view", "add", "change", "delete"):
                ModuleRight.objects.get_or_create(
                    role=self.admin.role, module=module, action=action
                )
        c = APIClient()
        c.force_authenticate(self.admin)
        return c

    def _candidate_client(self):
        """Individual + assessment view rights (mirrors the seeded dev
        environment, where individuals can take published assessments)."""
        from rest_framework.test import APIClient

        ModuleRight.objects.get_or_create(
            role=self.candidate.role, module="assessment", action="view"
        )
        c = APIClient()
        c.force_authenticate(self.candidate)
        return c


def _mcq(created_by, title, n_options=4, correct_idx=1):
    q = _make_question(
        created_by, "MCQ_TEXT_IMAGE", "BINARY", title, question_text_1=f"{title} text"
    )
    for i in range(n_options):
        ResponseOption.objects.create(
            question=q,
            sub_question_index=0,
            option_type="TEXT",
            text_value=f"opt{i}",
            is_correct=(i == correct_idx),
            order=i,
        )
    return q


# ---------------------------------------------------------------------------
# §1/§2/§4/§33 — static delivery order is EXACTLY the assigned order
# ---------------------------------------------------------------------------


class StaticDisplayOrderTest(Report7Base):
    def build_tree(self, display_order="STATIC"):
        """3 L1 sections x 2 L2 subsections x 3 questions = 18 questions."""
        ass = Assessment.objects.create(
            title="R7 static order test",
            assessment_type="normal",
            status="published",
            display_order=display_order,
            created_by=self.admin,
        )
        qs = [_mcq(self.admin, f"Q{i+1}") for i in range(18)]
        idx = 0
        for s in range(3):
            l1 = AssessmentSection.objects.create(
                assessment=ass, title=f"Sec{s+1}", level=1, order=s + 1
            )
            for sub in range(2):
                l2 = AssessmentSection.objects.create(
                    assessment=ass,
                    title=f"Sec{s+1}.{sub+1}",
                    level=2,
                    parent=l1,
                    order=sub + 1,
                )
                for _ in range(3):
                    AssessmentQuestion.objects.create(section=l2, question=qs[idx], order=idx + 1)
                    idx += 1
        return ass, qs

    def _session_attempts(self, ass):
        session = AssessmentSession.objects.create(assessment=ass, candidate=self.candidate)
        for aq in AssessmentQuestion.objects.filter(section__assessment=ass):
            QuestionAttempt.objects.get_or_create(
                session=session,
                question=aq.question,
                sub_question_index=aq.sub_question_index,
                defaults={"section": aq.section, "status": "not_attempted"},
            )
        return session

    def test_static_order_is_assigned_dfs_order(self):
        """§1/§2: questions delivered in exactly the assigned order — a
        depth-first walk of the section tree, each leaf's questions in their
        assigned order."""
        ass, qs = self.build_tree()
        session = self._session_attempts(ass)
        attempts = list(session.question_attempts.select_related("question", "section"))
        ordered = compute_delivery_order(ass, attempts, session.id)
        titles = [att.question.question_title for _, att in ordered]
        self.assertEqual(titles, [f"Q{i+1}" for i in range(18)])

    def test_static_order_stable_across_fetches(self):
        """§33: the static order is identical on every fetch (the old bug
        returned a jumbled/reverse order)."""
        ass, qs = self.build_tree()
        session = self._session_attempts(ass)
        attempts = list(session.question_attempts.select_related("question", "section"))
        o1 = [
            att.question.question_title
            for _, att in compute_delivery_order(ass, attempts, session.id)
        ]
        o2 = [
            att.question.question_title
            for _, att in compute_delivery_order(ass, attempts, session.id)
        ]
        self.assertEqual(o1, o2)
        self.assertEqual(o1, [f"Q{i+1}" for i in range(18)])

    def test_assessment_level_random_shuffles_whole_set(self):
        """§7: assessment-level RANDOM shuffles the entire question set."""
        ass, qs = self.build_tree(display_order="RANDOM")
        session = self._session_attempts(ass)
        attempts = list(session.question_attempts.select_related("question", "section"))
        titles = [
            att.question.question_title
            for _, att in compute_delivery_order(ass, attempts, session.id)
        ]
        self.assertEqual(sorted(titles), sorted([f"Q{i+1}" for i in range(18)]))
        # Extremely unlikely to be the identity for 18 items, but stay robust:
        self.assertNotEqual(titles, [f"Q{i+1}" for i in range(18)])
        # Stable within the same session:
        titles2 = [
            att.question.question_title
            for _, att in compute_delivery_order(ass, attempts, session.id)
        ]
        self.assertEqual(titles, titles2)

    def test_random_cascade_below_random_section_only(self):
        """§8: RANDOM set at a subsection shuffles ITS questions + child
        subsections, while parent-level sections keep their static order."""
        ass, qs = self.build_tree()
        # RANDOM only on Sec2's two L2 children:
        for l2 in AssessmentSection.objects.filter(
            assessment=ass, level=2, title__startswith="Sec2"
        ):
            l2.order_mode = "RANDOM"
            l2.save()
        session = self._session_attempts(ass)
        attempts = list(session.question_attempts.select_related("question", "section"))
        titles = [
            att.question.question_title
            for _, att in compute_delivery_order(ass, attempts, session.id)
        ]

        # Sec1 (Q1-6) and Sec3 (Q13-18) stay in assigned order:
        self.assertEqual(titles[0:6], [f"Q{i+1}" for i in range(6)])
        self.assertEqual(titles[12:18], [f"Q{i+13}" for i in range(6)])
        # Sec2's questions are shuffled within the section's slot:
        sec2 = titles[6:12]
        self.assertEqual(sorted(sec2), sorted([f"Q{i+7}" for i in range(6)]))

    def test_sidebar_metadata_present(self):
        """§3/§42/§43: rows carry section titles, paths, levels and a static
        order index for the TEST PROGRESS sidebar."""
        ass, qs = self.build_tree()
        client = self._candidate_client()
        r = client.post(f"/api/assessments/{ass.id}/start_session/")
        sid = r.json()["data"]["id"]
        r = client.get(f"/api/assessments/sessions/{sid}/questions/")
        rows = r.json()["data"]
        self.assertEqual(len(rows), 18)
        self.assertEqual(rows[0]["section_title"], "Sec1.1")
        self.assertEqual(rows[0]["section_path"], "Sec1 > Sec1.1")
        self.assertEqual(rows[0]["section_level"], 2)
        self.assertEqual(rows[0]["static_order_index"], 0)
        # Static indices form 0..17:
        self.assertEqual(sorted(row["static_order_index"] for row in rows), list(range(18)))

    def test_all_sub_question_attempts_seeded_upfront(self):
        """§10/§19: one row per sub-question from the START — the list never
        grows mid-session."""
        # 1f-style question with 3 sub-questions
        q_multi = _make_question(
            self.admin,
            "MCQ_IMAGE_FLASH_MULTI",
            "BINARY",
            "Q multi",
            sub_question_count=3,
            sub_question_texts=["a", "b", "c"],
        )
        for sqi in range(3):
            for k in range(4):
                ResponseOption.objects.create(
                    question=q_multi,
                    sub_question_index=sqi,
                    option_type="TEXT",
                    text_value=f"o{k}",
                    is_correct=(k == 1),
                    order=k,
                )
        ass = Assessment.objects.create(
            title="R7 subq seed test",
            assessment_type="normal",
            status="published",
            created_by=self.admin,
        )
        sec = AssessmentSection.objects.create(assessment=ass, title="S", level=1, order=1)
        AssessmentQuestion.objects.create(section=sec, question=q_multi, order=1)
        AssessmentQuestion.objects.create(section=sec, question=_mcq(self.admin, "Qx"), order=2)

        client = self._candidate_client()
        r = client.post(f"/api/assessments/{ass.id}/start_session/")
        sid = r.json()["data"]["id"]
        r = client.get(f"/api/assessments/sessions/{sid}/questions/")
        rows = r.json()["data"]
        # 1 multi (3 rows) + 1 single = 4 rows — STABLE before any answering:
        self.assertEqual(len(rows), 4)
        # Fetch again — still 4 (never grows):
        r = client.get(f"/api/assessments/sessions/{sid}/questions/")
        self.assertEqual(len(r.json()["data"]), 4)

    def test_answer_attempt_gets_correct_section(self):
        """§18/§42: on-the-fly attempts route to the question's ASSIGNED
        section, not assessment.sections.first()."""
        ass, qs = self.build_tree()
        session = self._session_attempts(ass)
        # Simulate answering the LAST section's question via the API flow:
        target = AssessmentQuestion.objects.filter(
            section__assessment=ass, section__title="Sec3.2"
        ).first()
        QuestionAttempt.objects.get_or_create(
            session=session,
            question=target.question,
            sub_question_index=0,
            defaults={"section": None, "status": "not_attempted"},
        )
        # Use the view's correction logic via the answer endpoint:
        client = self._candidate_client()
        opt = target.question.options.filter(is_correct=True).first()
        r = client.post(
            f"/api/assessments/sessions/{session.id}/answer/",
            {
                "question_id": target.question.id,
                "sub_question_index": 0,
                "raw_answer": {"selected_option_ids": [opt.id]},
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        att = QuestionAttempt.objects.get(
            session=session, question=target.question, sub_question_index=0
        )
        self.assertEqual(att.section, target.section)

    def test_resume_lands_on_first_unanswered_and_counts_stable(self):
        """§9/§18/§19: answers rehydrate — the questions payload returns
        attempted rows with raw_answer; counts derive from the server."""
        ass, qs = self.build_tree()
        client = self._candidate_client()
        r = client.post(f"/api/assessments/{ass.id}/start_session/")
        sid = r.json()["data"]["id"]
        # Answer the first 5 questions:
        for i in range(5):
            opt = qs[i].options.filter(is_correct=True).first()
            r = client.post(
                f"/api/assessments/sessions/{sid}/answer/",
                {
                    "question_id": qs[i].id,
                    "sub_question_index": 0,
                    "raw_answer": {"selected_option_ids": [opt.id]},
                },
                format="json",
            )
            self.assertEqual(r.status_code, 200)
        # Suspend + refetch (the player's resume path):
        client.post(f"/api/assessments/sessions/{sid}/suspend/")
        r = client.get(f"/api/assessments/sessions/{sid}/questions/")
        rows = r.json()["data"]
        attempted = [row for row in rows if row["raw_answer"]]
        self.assertEqual(len(attempted), 5)
        # First unanswered is Q6 (static index 5):
        self.assertIsNone(rows[5]["raw_answer"])
        # Row count unchanged (18):
        self.assertEqual(len(rows), 18)


# ---------------------------------------------------------------------------
# §11 — timer can be set at only ONE level (SRS §5.2)
# ---------------------------------------------------------------------------


class TimerHierarchyTest(Report7Base):
    def setUp(self):
        self.ass = Assessment.objects.create(
            title="R7 timer test",
            assessment_type="normal",
            status="draft",
            timer_level="assessment",
            created_by=self.admin,
        )
        self.l1 = AssessmentSection.objects.create(
            assessment=self.ass, title="L1a", level=1, order=1
        )
        self.l2 = AssessmentSection.objects.create(
            assessment=self.ass, title="L2a", level=2, parent=self.l1, order=1
        )

    def test_section_timer_rejected_at_assessment_level(self):
        c = self._granted_admin_client()
        r = c.post(
            f"/api/assessments/{self.ass.id}/sections/",
            {"title": "Bad", "duration_seconds": 300},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"]["code"], "timer_level_conflict")

    def test_section_timer_rejected_at_wrong_level(self):
        self.ass.timer_level = "level2"
        self.ass.save()
        c = self._granted_admin_client()
        # L1 section with a timer while timer_level=level2 → rejected:
        r = c.patch(
            f"/api/assessments/{self.ass.id}/sections/{self.l1.id}/",
            {"duration_seconds": 300},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        # L2 section with a timer → accepted:
        r = c.patch(
            f"/api/assessments/{self.ass.id}/sections/{self.l2.id}/",
            {"duration_seconds": 240},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_assessment_update_rejects_conflicting_timer_level(self):
        # Set an L2 timer first:
        self.ass.timer_level = "level2"
        self.ass.save()
        self.l2.duration_seconds = 240
        self.l2.save()
        c = self._granted_admin_client()
        # Switching to level1 while L2 holds a timer → 400, nothing applied:
        r = c.patch(f"/api/assessments/{self.ass.id}/", {"timer_level": "level1"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.ass.refresh_from_db()
        self.assertEqual(self.ass.timer_level, "level2")

    def test_question_timer_requires_question_level(self):
        self.ass.timer_level = "level2"
        self.ass.save()
        AssessmentQuestion.objects.create(section=self.l2, question=_mcq(self.admin, "TQ"), order=1)
        c = self._granted_admin_client()
        r = c.post(
            f"/api/assessments/{self.ass.id}/sections/{self.l2.id}/questions/",
            {"question": _mcq(self.admin, "TQ2").id, "duration_seconds": 60},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"]["code"], "timer_level_conflict")

    def test_section_display_path(self):
        """§3: full root→leaf path helper."""
        sections = list(self.ass.sections.all())
        path = section_display_path(self.l2, sections)
        self.assertEqual(path, "L1a > L2a")


# ---------------------------------------------------------------------------
# §12/§34 — assignment order values are set and lists are ascending
# ---------------------------------------------------------------------------


class AssignmentOrderTest(Report7Base):
    def test_sections_get_sequential_order_on_create(self):
        ass = Assessment.objects.create(
            title="R7 order set test",
            assessment_type="normal",
            status="draft",
            created_by=self.admin,
        )
        c = self._granted_admin_client()
        for i in range(3):
            r = c.post(f"/api/assessments/{ass.id}/sections/", {"title": f"S{i+1}"}, format="json")
            self.assertEqual(r.status_code, 201)
        orders = list(
            AssessmentSection.objects.filter(assessment=ass).values_list("order", flat=True)
        )
        self.assertEqual(orders, [1, 2, 3])

    def test_questions_get_sequential_order_on_assign(self):
        ass = Assessment.objects.create(
            title="R7 q order test",
            assessment_type="normal",
            status="draft",
            created_by=self.admin,
        )
        sec = AssessmentSection.objects.create(assessment=ass, title="S", level=1, order=1)
        c = self._granted_admin_client()
        qids = []
        for i in range(4):
            q = _mcq(self.admin, f"AQ{i+1}")
            qids.append(q.id)
            r = c.post(
                f"/api/assessments/{ass.id}/sections/{sec.id}/questions/",
                {"question": q.id},
                format="json",
            )
            self.assertEqual(r.status_code, 201)
        rows = list(
            AssessmentQuestion.objects.filter(section=sec).values_list("question_id", "order")
        )
        self.assertEqual([r[1] for r in rows], [1, 2, 3, 4])
        self.assertEqual([r[0] for r in rows], qids)

    def test_section_list_is_ascending(self):
        ass = Assessment.objects.create(
            title="R7 list order test",
            assessment_type="normal",
            status="draft",
            created_by=self.admin,
        )
        c = self._granted_admin_client()
        for i in range(4):
            c.post(f"/api/assessments/{ass.id}/sections/", {"title": f"S{i+1}"}, format="json")
        r = c.get(f"/api/assessments/{ass.id}/sections/")
        payload = r.json()["data"]
        sections = payload["results"] if isinstance(payload, dict) else payload
        titles = [s["title"] for s in sections]
        self.assertEqual(titles, ["S1", "S2", "S3", "S4"])


# ---------------------------------------------------------------------------
# §21 — section timer context reaches the player payload
# ---------------------------------------------------------------------------


class SectionTimerContextTest(Report7Base):
    def test_governing_section_duration_in_payload(self):
        ass = Assessment.objects.create(
            title="R7 timer ctx test",
            assessment_type="normal",
            status="published",
            timer_level="level1",
            created_by=self.admin,
        )
        l1 = AssessmentSection.objects.create(
            assessment=ass, title="T Sec", level=1, order=1, duration_seconds=240
        )
        AssessmentQuestion.objects.create(section=l1, question=_mcq(self.admin, "TQ"), order=1)
        c = self._candidate_client()
        r = c.post(f"/api/assessments/{ass.id}/start_session/")
        sid = r.json()["data"]["id"]
        r = c.get(f"/api/assessments/sessions/{sid}/questions/")
        rows = r.json()["data"]
        self.assertEqual(rows[0]["timer_section_id"], l1.id)
        self.assertEqual(rows[0]["section_duration_seconds"], 240)


# ---------------------------------------------------------------------------
# §22/§24-§27 — scoring per Report 7
# ---------------------------------------------------------------------------


class Report7ScoringTest(Report7Base):
    def test_multi_answer_mcq_one_correct_one_wrong_scores_half(self):
        """§27: 1 correct + 1 wrong of 2 correct → 1/2 (was 0/2)."""
        q = _make_question(
            self.admin,
            "MCQ_TEXT_IMAGE_IMG_OPTIONS",
            "BINARY",
            "MA MCQ",
            question_text_1="Pick two.",
        )
        opts = []
        for i, correct in enumerate([True, True, False, False, False]):
            opts.append(
                ResponseOption.objects.create(
                    question=q,
                    sub_question_index=0,
                    option_type="IMAGE",
                    text_value="",
                    image_file=f"data:image/png;base64,X{i}",
                    is_correct=correct,
                    order=i,
                )
            )
        correct_ids = [o.id for o in opts if o.is_correct]
        wrong_ids = [o.id for o in opts if not o.is_correct]
        score, max_score = score_question(
            q, {"selected_option_ids": [correct_ids[0], wrong_ids[0]]}, 0
        )
        self.assertEqual((score, max_score), (1.0, 2.0))
        # All correct → 2/2:
        score, max_score = score_question(q, {"selected_option_ids": correct_ids}, 0)
        self.assertEqual((score, max_score), (2.0, 2.0))

    def test_multi_answer_all_three_correct_scores_three(self):
        """§22: three correct answers → combined 3."""
        q = _make_question(
            self.admin, "MCQ_TEXT_IMAGE", "BINARY", "MA3", question_text_1="Pick three."
        )
        correct = []
        for i in range(5):
            o = ResponseOption.objects.create(
                question=q,
                sub_question_index=0,
                option_type="TEXT",
                text_value=f"o{i}",
                is_correct=(i < 3),
                order=i,
            )
            if i < 3:
                correct.append(o.id)
        score, max_score = score_question(q, {"selected_option_ids": correct}, 0)
        self.assertEqual((score, max_score), (3.0, 3.0))

    def test_fitb_multi_field_scores_three_fields(self):
        """§24: 3 fields all correct → 3/3."""
        q = _make_question(
            self.admin, "FITB_MULTI_FIELD", "PARTIAL", "FITB3", question_text_1="Fill."
        )
        for i, ans in enumerate(["Paris", "Blue", "Two"]):
            opt = ResponseOption.objects.create(
                question=q,
                sub_question_index=0,
                option_type="TEXT",
                text_value=f"F{i+1}",
                order=i,
            )
            CorrectAnswer.objects.create(response_option=opt, answer_text=ans, order=0)
        score, max_score = score_question(q, {"answers": ["Paris", "Blue", "Two"]}, 0)
        self.assertEqual((score, max_score), (3.0, 3.0))

    def test_flash_recall_scores_against_flash_items(self):
        """§25/§26: 10 flash items, all 10 recalled (any order) → 10/10 —
        scoring works even when the author entered no manual
        correct_answers (the flash items themselves are the answer key)."""
        q = _make_question(
            self.admin,
            "FITB_WORD_FLASH_MULTI",
            "PARTIAL",
            "FLASH10",
            question_text_1="Recall.",
            flash_interval_ms=500,
        )
        words = [f"w{i+1}" for i in range(10)]
        for i, w in enumerate(words):
            FlashItem.objects.create(
                question=q, item_type="TEXT", text_value=w, order=i, is_in_display_pool=True
            )
            # NO CorrectAnswer rows — flash items are the answer key now.
        shuffled = list(reversed(words))  # any order
        score, max_score = score_question(q, {"answers": shuffled}, 0)
        self.assertEqual((score, max_score), (10.0, 10.0))

    def test_flash_recall_counts_each_answer_once(self):
        """Duplicate entries don't double-score; wrong entries score 0."""
        q = _make_question(
            self.admin,
            "FITB_WORD_FLASH_MULTI",
            "PARTIAL",
            "FLASH2",
            question_text_1="Recall.",
            flash_interval_ms=500,
        )
        for i, w in enumerate(["alpha", "bravo"]):
            FlashItem.objects.create(
                question=q, item_type="TEXT", text_value=w, order=i, is_in_display_pool=True
            )
        score, max_score = score_question(q, {"answers": ["alpha", "alpha", "wrong", "bravo"]}, 0)
        self.assertEqual((score, max_score), (2.0, 2.0))

    def test_bookmarked_attempt_with_answer_still_scores(self):
        """§24: a saved answer scores even when the candidate also
        bookmarked the question (bookmarking never discards an answer)."""
        q = _mcq(self.admin, "BM Q")
        ass = Assessment.objects.create(
            title="R7 bm test", assessment_type="normal", status="published", created_by=self.admin
        )
        sec = AssessmentSection.objects.create(assessment=ass, title="S", level=1, order=1)
        AssessmentQuestion.objects.create(section=sec, question=q, order=1)
        session = AssessmentSession.objects.create(assessment=ass, candidate=self.candidate)
        opt = q.options.filter(is_correct=True).first()
        QuestionAttempt.objects.create(
            session=session,
            question=q,
            section=sec,
            sub_question_index=0,
            status="bookmarked",
            raw_answer={"selected_option_ids": [opt.id]},
        )
        session = calculate_session_scores(session)
        att = session.question_attempts.get(question=q)
        self.assertEqual(att.score, 1.0)

    def test_combined_sub_question_scores_aggregate(self):
        """§22: a 1f with 3 correct sub-answers scores 3/3 combined via the
        session totals (parent question = wrapper)."""
        q = _make_question(
            self.admin,
            "MCQ_IMAGE_FLASH_MULTI",
            "BINARY",
            "IF3",
            sub_question_count=3,
            sub_question_texts=["a", "b", "c"],
        )
        for sqi in range(3):
            for k in range(4):
                ResponseOption.objects.create(
                    question=q,
                    sub_question_index=sqi,
                    option_type="TEXT",
                    text_value=f"o{k}",
                    is_correct=(k == 1),
                    order=k,
                )
        ass = Assessment.objects.create(
            title="R7 1f test",
            assessment_type="normal",
            status="published",
            created_by=self.admin,
        )
        sec = AssessmentSection.objects.create(assessment=ass, title="S", level=1, order=1)
        AssessmentQuestion.objects.create(section=sec, question=q, order=1)
        session = AssessmentSession.objects.create(assessment=ass, candidate=self.candidate)
        for sqi in range(3):
            correct_opt = q.options.filter(sub_question_index=sqi, is_correct=True).first()
            QuestionAttempt.objects.create(
                session=session,
                question=q,
                section=sec,
                sub_question_index=sqi,
                status="attempted",
                raw_answer={"selected_option_ids": [correct_opt.id]},
            )
        session = calculate_session_scores(session)
        self.assertEqual(session.total_score, 3.0)
        self.assertEqual(session.max_score, 3.0)

    def test_question_type_label_renamed(self):
        """§23: 1f label reads 'Multiple Answers'."""
        q = _make_question(self.admin, "MCQ_IMAGE_FLASH_MULTI", "BINARY", "Label check")
        self.assertIn("Multiple Answers", q.get_question_type_display())
        self.assertNotIn("Multiple Questions", q.get_question_type_display())
