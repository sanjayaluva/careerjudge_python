"""Tests for the Task Management module."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from apps.tasks.models import Concern, Task, TaskExtensionRequest, TaskSpec


class TaskBaseTestCase(APITestCase):
    """Base test case with admin + sme user setup."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_role, _ = Role.objects.get_or_create(
            name="cj_admin", defaults={"is_system": True, "is_frozen": True}
        )
        cls.sme_role, _ = Role.objects.get_or_create(
            name="sme", defaults={"is_system": True, "is_frozen": True}
        )
        cls.reviewer_role, _ = Role.objects.get_or_create(
            name="reviewer", defaults={"is_system": True, "is_frozen": True}
        )
        cls.admin = User.objects.create_user(
            email="admin@test.com", password="pw12345", is_active=True, role=cls.admin_role
        )
        cls.sme = User.objects.create_user(
            email="sme@test.com", password="pw12345", is_active=True, role=cls.sme_role
        )
        cls.reviewer = User.objects.create_user(
            email="reviewer@test.com", password="pw12345", is_active=True, role=cls.reviewer_role
        )

    @staticmethod
    def _extract_results(resp_json):
        """Extract results list from either paginated or plain response."""
        if isinstance(resp_json, list):
            return resp_json
        if isinstance(resp_json, dict):
            if "results" in resp_json:
                return resp_json["results"]
            if "data" in resp_json:
                data = resp_json["data"]
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "results" in data:
                    return data["results"]
        return resp_json


class TaskLifecycleTests(TaskBaseTestCase):
    """Test task create → start → submit → approve flow."""

    def test_admin_can_create_task(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            "/api/tasks/",
            {
                "title": "Create MCQ for Quant",
                "description": "Please create 5 MCQs under Quant > Algebra.",
                "assigned_to": self.sme.id,
                "assignee_role": "sme",
                "priority": "high",
                "due_date": (timezone.now() + timedelta(days=7)).isoformat(),
                "spec": {
                    "qb_category": "Quant",
                    "qb_subcategory": "Algebra",
                    "question_type": "mcq_text",
                    "num_questions": 5,
                    "num_options": 4,
                    "num_correct_options": 1,
                },
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["assignee_role"], "sme")
        self.assertTrue(data["task_id"].startswith("TSK-"))
        self.assertEqual(data["spec"]["num_questions"], 5)
        # Notification created for assignee
        self.assertEqual(self.sme.notifications.count(), 1)

    def test_admin_can_create_sme_task_with_multiple_spec_rows(self):
        """D9: SME multi-category task sheet — multiple category/difficulty/
        type rows in a single task via the `specs` list."""
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            "/api/tasks/",
            {
                "title": "Create MCQs across categories",
                "description": "5 Easy Quant MCQs + 3 Hard Verbal FITB.",
                "assigned_to": self.sme.id,
                "assignee_role": "sme",
                "specs": [
                    {
                        "qb_category": "Quant",
                        "qb_subcategory": "Algebra",
                        "question_type": "mcq_text",
                        "num_questions": 5,
                        "difficulty_level": "easy",
                    },
                    {
                        "qb_category": "Verbal",
                        "qb_subcategory": "Comprehension",
                        "question_type": "fitb_text",
                        "num_questions": 3,
                        "difficulty_level": "hard",
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()["data"]
        self.assertEqual(len(data["specs"]), 2)
        categories = {row["qb_category"] for row in data["specs"]}
        self.assertEqual(categories, {"Quant", "Verbal"})
        # Backward-compat convenience: `spec` still exposes the first row.
        self.assertEqual(data["spec"]["qb_category"], "Quant")
        task = Task.objects.get(task_id=data["task_id"])
        self.assertEqual(task.specs.count(), 2)

    def test_updating_specs_replaces_existing_rows(self):
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        TaskSpec.objects.create(task=task, qb_category="Old", num_questions=1)
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            f"/api/tasks/{task.id}/",
            {"specs": [{"qb_category": "New1", "num_questions": 2}, {"qb_category": "New2"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        task.refresh_from_db()
        self.assertEqual(task.specs.count(), 2)
        categories = set(task.specs.values_list("qb_category", flat=True))
        self.assertEqual(categories, {"New1", "New2"})

    def test_task_creation_notifies_helpdesk_and_admin(self):
        """D9 §3.1: helpdesk (and admin) must be notified when a task is assigned."""
        helpdesk_role, _ = Role.objects.get_or_create(
            name="helpdesk", defaults={"is_system": True, "is_frozen": True}
        )
        helpdesk_user = User.objects.create_user(
            email="helpdesk@test.com", password="pw12345", is_active=True, role=helpdesk_role
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            "/api/tasks/",
            {
                "title": "Create MCQ for Quant",
                "description": "Please create 5 MCQs under Quant > Algebra.",
                "assigned_to": self.sme.id,
                "assignee_role": "sme",
                "priority": "high",
                "due_date": (timezone.now() + timedelta(days=7)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(helpdesk_user.notifications.count(), 1)
        self.assertEqual(self.admin.notifications.count(), 1)

    def test_non_admin_cannot_create_task(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/tasks/",
            {
                "title": "Self-assign",
                "description": "Try to assign to myself.",
                "assigned_to": self.sme.id,
                "assignee_role": "sme",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_assignee_role_mismatch_rejected(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            "/api/tasks/",
            {
                "title": "Wrong role",
                "description": "SME user but role says reviewer.",
                "assigned_to": self.sme.id,
                "assignee_role": "reviewer",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_assignee_can_start_task(self):
        task = Task.objects.create(
            title="Test task",
            description="desc",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            due_date=timezone.now() + timedelta(days=3),
        )
        self.client.force_authenticate(self.sme)
        resp = self.client.post(f"/api/tasks/{task.id}/start/")
        self.assertEqual(resp.status_code, 200, resp.content)
        task.refresh_from_db()
        self.assertEqual(task.status, "in_progress")
        self.assertIsNotNone(task.started_at)
        # Progress update created
        self.assertEqual(task.progress_updates.count(), 1)
        # Admin notified
        self.assertEqual(self.admin.notifications.count(), 1)

    def test_non_assignee_cannot_start(self):
        task = Task.objects.create(
            title="Test",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.client.force_authenticate(self.reviewer)
        resp = self.client.post(f"/api/tasks/{task.id}/start/")
        # 403 (forbidden) or 404 (not found) both acceptable
        self.assertIn(resp.status_code, [403, 404], resp.content)

    def test_assignee_can_submit_for_review(self):
        task = Task.objects.create(
            title="Test",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            status="in_progress",
        )
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            f"/api/tasks/{task.id}/submit/",
            {"message": "All 5 questions added."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        task.refresh_from_db()
        self.assertEqual(task.status, "awaiting_review")

    def test_admin_can_approve_completion(self):
        task = Task.objects.create(
            title="Test",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            status="awaiting_review",
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/tasks/{task.id}/approve/",
            {"comment": "Great work."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.approval_comment, "Great work.")
        self.assertIsNotNone(task.completed_at)
        # Assignee notified
        self.assertEqual(self.sme.notifications.count(), 1)

    def test_admin_can_cancel_with_reason(self):
        task = Task.objects.create(
            title="Test",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/tasks/{task.id}/cancel/",
            {"reason": "No longer needed."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        task.refresh_from_db()
        self.assertEqual(task.status, "cancelled")
        self.assertEqual(task.cancellation_reason, "No longer needed.")

    def test_cancel_without_reason_fails(self):
        task = Task.objects.create(
            title="Test",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f"/api/tasks/{task.id}/cancel/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_non_admin_cannot_cancel(self):
        task = Task.objects.create(
            title="Test",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            f"/api/tasks/{task.id}/cancel/",
            {"reason": "I want to quit."},
            format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)


class CancelledTaskNoLongerActionableTests(TaskBaseTestCase):
    """D9: a cancelled task should no longer be actionable, even though it
    stays visible/readable for record-keeping."""

    def _cancelled_task(self):
        task = Task.objects.create(
            title="Test",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            status="in_progress",
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/tasks/{task.id}/cancel/",
            {"reason": "No longer needed."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        task.refresh_from_db()
        return task

    def test_assignee_cannot_start_cancelled_task(self):
        task = self._cancelled_task()
        self.client.force_authenticate(self.sme)
        resp = self.client.post(f"/api/tasks/{task.id}/start/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_assignee_cannot_submit_cancelled_task(self):
        task = self._cancelled_task()
        self.client.force_authenticate(self.sme)
        resp = self.client.post(f"/api/tasks/{task.id}/submit/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_assignee_cannot_post_progress_on_cancelled_task(self):
        task = self._cancelled_task()
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            f"/api/tasks/{task.id}/progress/", {"message": "still working"}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("cancelled", resp.json()["detail"].lower())

    def test_admin_cannot_post_progress_on_cancelled_task(self):
        task = self._cancelled_task()
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f"/api/tasks/{task.id}/progress/", {"message": "hi"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_assignee_cannot_request_extension_on_cancelled_task(self):
        task = self._cancelled_task()
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            f"/api/tasks/{task.id}/extensions/",
            {"requested_due_date": (timezone.now() + timedelta(days=3)).isoformat()},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_admin_cannot_request_update_on_cancelled_task(self):
        task = self._cancelled_task()
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f"/api/tasks/{task.id}/request_update/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_cancelled_task_is_still_visible_to_assignee(self):
        """Cancelled tasks stay readable (audit trail) even though they're no
        longer actionable — only the mutating endpoints are blocked."""
        task = self._cancelled_task()
        self.client.force_authenticate(self.sme)
        resp = self.client.get(f"/api/tasks/{task.id}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "cancelled")


class TaskVisibilityTests(TaskBaseTestCase):
    """Test that assignees only see their own tasks; admin sees all."""

    def test_assignee_sees_only_own_tasks(self):
        Task.objects.create(
            title="My task",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        Task.objects.create(
            title="Reviewer task",
            description="",
            assigned_by=self.admin,
            assigned_to=self.reviewer,
            assignee_role="reviewer",
        )
        self.client.force_authenticate(self.sme)
        resp = self.client.get("/api/tasks/")
        self.assertEqual(resp.status_code, 200, resp.content)
        results = self._extract_results(resp.json())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "My task")

    def test_admin_sees_all_tasks(self):
        Task.objects.create(
            title="My task",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        Task.objects.create(
            title="Reviewer task",
            description="",
            assigned_by=self.admin,
            assigned_to=self.reviewer,
            assignee_role="reviewer",
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/tasks/")
        self.assertEqual(resp.status_code, 200, resp.content)
        results = self._extract_results(resp.json())
        self.assertEqual(len(results), 2)

    def test_my_tasks_endpoint(self):
        Task.objects.create(
            title="My task",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.client.force_authenticate(self.sme)
        resp = self.client.get("/api/tasks/my_tasks/")
        self.assertEqual(resp.status_code, 200, resp.content)
        results = self._extract_results(resp.json())
        self.assertEqual(len(results), 1)


class TaskProgressTests(TaskBaseTestCase):
    """Test progress updates + admin request update."""

    def test_assignee_can_post_progress(self):
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            f"/api/tasks/{task.id}/progress/",
            {"message": "3 of 5 done."},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        # Admin got notification
        self.assertEqual(self.admin.notifications.count(), 1)

    def test_admin_can_request_progress_update(self):
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/tasks/{task.id}/request_update/",
            {"message": "How's it going?"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        # Assignee got notification
        self.assertEqual(self.sme.notifications.count(), 1)
        # Update flagged as admin request
        update = task.progress_updates.first()
        self.assertTrue(update.is_admin_request)


class TaskExtensionTests(TaskBaseTestCase):
    """Test extension request flow."""

    def test_assignee_can_request_extension(self):
        due = timezone.now() + timedelta(days=2)
        new_due = timezone.now() + timedelta(days=5)
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            due_date=due,
        )
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            f"/api/tasks/{task.id}/extensions/",
            {"requested_due_date": new_due.isoformat(), "reason": "Need more time."},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        # Admin got notification
        self.assertEqual(self.admin.notifications.count(), 1)
        ext = TaskExtensionRequest.objects.get(task=task)
        self.assertEqual(ext.status, "pending")
        self.assertEqual(ext.current_due_date, due)

    def test_admin_can_approve_extension_updates_due_date(self):
        due = timezone.now() + timedelta(days=2)
        new_due = timezone.now() + timedelta(days=5)
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            due_date=due,
        )
        ext = TaskExtensionRequest.objects.create(
            task=task,
            requested_by=self.sme,
            current_due_date=due,
            requested_due_date=new_due,
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/tasks/extensions/{ext.id}/approve/",
            {"comment": "OK, approved."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        ext.refresh_from_db()
        self.assertEqual(ext.status, "approved")
        task.refresh_from_db()
        self.assertEqual(task.due_date, new_due)

    def test_admin_can_decline_extension(self):
        due = timezone.now() + timedelta(days=2)
        new_due = timezone.now() + timedelta(days=5)
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            due_date=due,
        )
        ext = TaskExtensionRequest.objects.create(
            task=task,
            requested_by=self.sme,
            current_due_date=due,
            requested_due_date=new_due,
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/tasks/extensions/{ext.id}/decline/",
            {"comment": "No, stick to original date."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        ext.refresh_from_db()
        self.assertEqual(ext.status, "declined")
        # Task due_date unchanged
        task.refresh_from_db()
        self.assertEqual(task.due_date, due)


class TaskModelTests(TaskBaseTestCase):
    """Test model-level helpers."""

    def test_task_id_is_unique(self):
        t1 = Task.objects.create(
            title="T1",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        t2 = Task.objects.create(
            title="T2",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.assertNotEqual(t1.task_id, t2.task_id)

    def test_is_overdue(self):
        past_due = timezone.now() - timedelta(days=1)
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            due_date=past_due,
        )
        self.assertTrue(task.is_overdue)

    def test_completed_task_not_overdue(self):
        past_due = timezone.now() - timedelta(days=1)
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
            due_date=past_due,
            status="completed",
        )
        self.assertFalse(task.is_overdue)

    def test_can_be_cancelled(self):
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.assertTrue(task.can_be_cancelled)
        task.status = "completed"
        task.save()
        self.assertFalse(task.can_be_cancelled)

    def test_can_be_approved_only_when_awaiting_review(self):
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.assertFalse(task.can_be_approved)
        task.status = "awaiting_review"
        task.save()
        self.assertTrue(task.can_be_approved)


class TaskSpecTests(TaskBaseTestCase):
    """Test TaskSpec one-to-one with Task."""

    def test_spec_creation(self):
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        TaskSpec.objects.create(
            task=task,
            qb_category="Quant",
            qb_subcategory="Algebra",
            question_type="mcq_text",
            num_questions=5,
            num_options=4,
            num_correct_options=1,
            difficulty_level="medium",
            cognitive_level="apply",
        )
        self.assertEqual(task.specs.count(), 1)
        self.assertEqual(task.specs.first().num_questions, 5)
        self.assertEqual(task.specs.first().difficulty_level, "medium")

    def test_a_task_can_have_multiple_spec_rows(self):
        """D9: SME multi-category task sheet — a single task can carry more
        than one category/difficulty/type row (task.specs is now a
        ForeignKey-backed collection, not a OneToOne)."""
        task = Task.objects.create(
            title="T",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        TaskSpec.objects.create(task=task, qb_category="Quant", num_questions=5)
        TaskSpec.objects.create(task=task, qb_category="Verbal", num_questions=3)
        self.assertEqual(task.specs.count(), 2)
        categories = set(task.specs.values_list("qb_category", flat=True))
        self.assertEqual(categories, {"Quant", "Verbal"})


class ConcernTests(TaskBaseTestCase):
    """D9: any user can raise a concern, routed to cj_admin + helpdesk."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.helpdesk_role, _ = Role.objects.get_or_create(
            name="helpdesk", defaults={"is_system": True, "is_frozen": True}
        )
        cls.helpdesk = User.objects.create_user(
            email="helpdesk@test.com", password="pw12345", is_active=True, role=cls.helpdesk_role
        )

    def test_user_can_raise_a_concern(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/tasks/concerns/",
            {"subject": "Can't access my task", "message": "The task link 404s."},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()["data"]
        self.assertEqual(data["subject"], "Can't access my task")
        self.assertEqual(data["status"], "open")
        concern = Concern.objects.get(id=data["id"])
        self.assertEqual(concern.raised_by, self.sme)

    def test_raising_a_concern_notifies_admin_and_helpdesk(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/tasks/concerns/",
            {"subject": "Question", "message": "Need help."},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin, title__icontains="Concern raised"
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.helpdesk, title__icontains="Concern raised"
            ).exists()
        )

    def test_concern_can_reference_a_task(self):
        task = Task.objects.create(
            title="Test",
            description="",
            assigned_by=self.admin,
            assigned_to=self.sme,
            assignee_role="sme",
        )
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/tasks/concerns/",
            {"subject": "Issue with task", "message": "Unclear spec.", "related_task": task.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["data"]["related_task"], task.id)

    def test_user_sees_only_own_concerns(self):
        Concern.objects.create(raised_by=self.sme, subject="Mine", message="x")
        Concern.objects.create(raised_by=self.reviewer, subject="Not mine", message="y")
        self.client.force_authenticate(self.sme)
        resp = self.client.get("/api/tasks/concerns/")
        results = self._extract_results(resp.json())
        subjects = {c["subject"] for c in results}
        self.assertEqual(subjects, {"Mine"})

    def test_admin_sees_all_concerns(self):
        Concern.objects.create(raised_by=self.sme, subject="Mine", message="x")
        Concern.objects.create(raised_by=self.reviewer, subject="Also mine", message="y")
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/tasks/concerns/")
        results = self._extract_results(resp.json())
        self.assertEqual(len(results), 2)

    def test_helpdesk_sees_all_concerns(self):
        Concern.objects.create(raised_by=self.sme, subject="Mine", message="x")
        self.client.force_authenticate(self.helpdesk)
        resp = self.client.get("/api/tasks/concerns/")
        results = self._extract_results(resp.json())
        self.assertEqual(len(results), 1)

    def test_admin_can_resolve_a_concern(self):
        concern = Concern.objects.create(raised_by=self.sme, subject="Mine", message="x")
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/tasks/concerns/{concern.id}/resolve/",
            {"comment": "Fixed it."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        concern.refresh_from_db()
        self.assertEqual(concern.status, "resolved")
        self.assertEqual(concern.resolved_by, self.admin)
        self.assertEqual(concern.resolution_comment, "Fixed it.")
        self.assertIsNotNone(concern.resolved_at)
        # The concern's author is notified of the resolution.
        self.assertTrue(
            Notification.objects.filter(recipient=self.sme, title__icontains="resolved").exists()
        )

    def test_non_admin_cannot_resolve_a_concern(self):
        """A non-admin who isn't the raiser can't even see the concern to
        resolve it (get_queryset scopes it out — 404, not a 403 leak)."""
        concern = Concern.objects.create(raised_by=self.sme, subject="Mine", message="x")
        self.client.force_authenticate(self.reviewer)
        resp = self.client.post(f"/api/tasks/concerns/{concern.id}/resolve/", {}, format="json")
        self.assertEqual(resp.status_code, 404, resp.content)

    def test_raiser_cannot_resolve_own_concern(self):
        """Only cj_admin/helpdesk can resolve — even the concern's own
        raiser (who CAN see it) is forbidden from resolving it themselves."""
        concern = Concern.objects.create(raised_by=self.sme, subject="Mine", message="x")
        self.client.force_authenticate(self.sme)
        resp = self.client.post(f"/api/tasks/concerns/{concern.id}/resolve/", {}, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_cannot_resolve_already_resolved_concern(self):
        concern = Concern.objects.create(
            raised_by=self.sme, subject="Mine", message="x", status="resolved"
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f"/api/tasks/concerns/{concern.id}/resolve/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_user_cannot_see_others_concern_detail(self):
        concern = Concern.objects.create(raised_by=self.reviewer, subject="Private", message="x")
        self.client.force_authenticate(self.sme)
        resp = self.client.get(f"/api/tasks/concerns/{concern.id}/")
        self.assertEqual(resp.status_code, 404)
