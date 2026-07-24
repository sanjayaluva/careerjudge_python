"""Tests for the Task Management module."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.tasks.models import Task, TaskExtensionRequest, TaskSpec


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
        self.assertEqual(task.spec.num_questions, 5)
        self.assertEqual(task.spec.difficulty_level, "medium")
