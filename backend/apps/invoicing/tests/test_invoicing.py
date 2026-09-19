"""Basic tests for the Invoicing module."""

from rest_framework.test import APITestCase

from apps.accounts.models import Role, User


class InvoicingBaseTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_role, _ = Role.objects.get_or_create(
            name="cj_admin", defaults={"is_system": True, "is_frozen": True}
        )
        cls.sme_role, _ = Role.objects.get_or_create(
            name="sme", defaults={"is_system": True, "is_frozen": True}
        )
        cls.admin = User.objects.create_user(
            email="admin@inv-test.com", password="pw12345", is_active=True, role=cls.admin_role
        )
        cls.sme = User.objects.create_user(
            email="sme@inv-test.com", password="pw12345", is_active=True, role=cls.sme_role
        )


class InvoiceTests(InvoicingBaseTestCase):
    def test_create_invoice(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {
                "invoice_type": "question_creation",
                "description": "Created 10 MCQ questions for Quant category",
                "amount": "5000.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "draft")
        self.assertTrue(data["invoice_number"].startswith("INV-"))

    def test_submit_invoice(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {"description": "Test invoice", "amount": "1000.00"},
            format="json",
        )
        inv_id = resp.json()["data"]["id"]
        resp = self.client.post(f"/api/invoicing/invoices/{inv_id}/submit/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"]["status"], "submitted")

    def test_admin_approve_invoice(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {"description": "To approve", "amount": "2000.00"},
            format="json",
        )
        inv_id = resp.json()["data"]["id"]
        self.client.post(f"/api/invoicing/invoices/{inv_id}/submit/")

        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/invoicing/invoices/{inv_id}/approve/",
            {"comment": "Approved for payment."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"]["status"], "approved")

    def test_admin_reject_invoice(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {"description": "To reject", "amount": "500.00"},
            format="json",
        )
        inv_id = resp.json()["data"]["id"]
        self.client.post(f"/api/invoicing/invoices/{inv_id}/submit/")

        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/invoicing/invoices/{inv_id}/reject/",
            {"comment": "Insufficient details."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"]["status"], "rejected")

    def test_cancel_invoice(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {"description": "To cancel", "amount": "300.00"},
            format="json",
        )
        inv_id = resp.json()["data"]["id"]
        resp = self.client.post(f"/api/invoicing/invoices/{inv_id}/cancel/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"]["status"], "cancelled")

    def test_admin_pay_invoice(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {"description": "To pay", "amount": "1500.00"},
            format="json",
        )
        inv_id = resp.json()["data"]["id"]
        self.client.post(f"/api/invoicing/invoices/{inv_id}/submit/")

        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/invoicing/invoices/{inv_id}/approve/")
        resp = self.client.post(
            f"/api/invoicing/invoices/{inv_id}/pay/",
            {"payment_reference": "BANK-REF-001"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"]["status"], "paid")

    def test_my_invoices(self):
        self.client.force_authenticate(self.sme)
        self.client.post(
            "/api/invoicing/invoices/",
            {"description": "My invoice", "amount": "800.00"},
            format="json",
        )
        resp = self.client.get("/api/invoicing/invoices/my_invoices/")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_pending_invoices_admin_only(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.get("/api/invoicing/invoices/pending/")
        self.assertEqual(resp.status_code, 403, resp.content)

        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/invoicing/invoices/pending/")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_non_empanelled_role_forbidden_from_creating_invoice(self):
        """H14: only empanelled roles (+ cj_admin) may create invoices."""
        individual_role, _ = Role.objects.get_or_create(
            name="individual", defaults={"is_system": True, "is_frozen": True}
        )
        individual = User.objects.create_user(
            email="individual@inv-test.com",
            password="pw12345",
            is_active=True,
            role=individual_role,
        )
        self.client.force_authenticate(individual)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {"description": "Not allowed", "amount": "100.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_empanelled_counsellor_can_create_invoice(self):
        """H14: counsellor is an empanelled role (Doc 4)."""
        counsellor_role, _ = Role.objects.get_or_create(
            name="counsellor", defaults={"is_system": True, "is_frozen": True}
        )
        counsellor = User.objects.create_user(
            email="counsellor@inv-test.com",
            password="pw12345",
            is_active=True,
            role=counsellor_role,
        )
        self.client.force_authenticate(counsellor)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {
                "invoice_type": "counseling",
                "description": "Counselled 5 sessions this month",
                "amount": "2500.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_non_admin_cannot_see_others_invoices(self):
        from apps.accounts.models import User

        other_sme = User.objects.create_user(
            email="other@inv-test.com", password="pw12345", is_active=True, role=self.sme_role
        )
        self.client.force_authenticate(other_sme)
        self.client.post(
            "/api/invoicing/invoices/",
            {"description": "Other's invoice", "amount": "100.00"},
            format="json",
        )

        self.client.force_authenticate(self.sme)
        resp = self.client.get("/api/invoicing/invoices/")
        results = resp.json().get("results", resp.json().get("data", []))
        # SME should not see other_sme's invoices
        self.assertFalse(any("Other" in r.get("description", "") for r in results))


class InvoicePatchGuardTests(InvoicingBaseTestCase):
    """E-PLT-7: PATCH guard on invoices."""

    def _draft(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {"description": "Editable", "amount": "1000.00"},
            format="json",
        )
        return resp.json()["data"]["id"]

    def test_creator_can_edit_draft(self):
        inv_id = self._draft()
        resp = self.client.patch(
            f"/api/invoicing/invoices/{inv_id}/",
            {"description": "Updated text"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_cannot_patch_status_directly(self):
        inv_id = self._draft()
        resp = self.client.patch(
            f"/api/invoicing/invoices/{inv_id}/",
            {"status": "paid"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_cannot_edit_after_submit(self):
        inv_id = self._draft()
        self.client.post(f"/api/invoicing/invoices/{inv_id}/submit/")
        resp = self.client.patch(
            f"/api/invoicing/invoices/{inv_id}/",
            {"description": "Too late"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)


class InvoiceItemTests(InvoicingBaseTestCase):
    """E-PLT-7: line-item CRUD."""

    def _draft(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/invoicing/invoices/",
            {"description": "With items", "amount": "0.00"},
            format="json",
        )
        return resp.json()["data"]["id"]

    def test_add_line_item_computes_total(self):
        inv_id = self._draft()
        resp = self.client.post(
            "/api/invoicing/invoice-items/",
            {"invoice": inv_id, "description": "10 MCQs", "quantity": 10, "unit_price": "50.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["data"]["total"], "500.00")

    def test_cannot_add_item_to_submitted_invoice(self):
        inv_id = self._draft()
        self.client.post(f"/api/invoicing/invoices/{inv_id}/submit/")
        resp = self.client.post(
            "/api/invoicing/invoice-items/",
            {"invoice": inv_id, "description": "x", "quantity": 1, "unit_price": "5.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_delete_line_item(self):
        inv_id = self._draft()
        resp = self.client.post(
            "/api/invoicing/invoice-items/",
            {"invoice": inv_id, "description": "row", "quantity": 1, "unit_price": "5.00"},
            format="json",
        )
        item_id = resp.json()["data"]["id"]
        resp = self.client.delete(f"/api/invoicing/invoice-items/{item_id}/")
        self.assertIn(resp.status_code, (200, 204), resp.content)
