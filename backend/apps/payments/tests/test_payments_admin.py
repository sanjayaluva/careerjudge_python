"""E-PLT-2: admin payment-authorise workflow."""

from decimal import Decimal

from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.payments.models import Payment


class PaymentAdminBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_role, _ = Role.objects.get_or_create(
            name="cj_admin", defaults={"is_system": True, "is_frozen": True}
        )
        cls.ind_role, _ = Role.objects.get_or_create(
            name="individual", defaults={"is_system": True, "is_frozen": True}
        )
        cls.admin = User.objects.create_user(
            email="admin@pay-test.com", password="pw12345", is_active=True, role=cls.admin_role
        )
        cls.user = User.objects.create_user(
            email="u@pay-test.com", password="pw12345", is_active=True, role=cls.ind_role
        )


class AuthoriseTests(PaymentAdminBase):
    def _pending(self):
        return Payment.objects.create(
            user=self.user, module="assessment", item_id=99, amount=Decimal("25.00"),
            status="pending",
        )

    def test_admin_authorises_pending_payment(self):
        p = self._pending()
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f"/api/payments/{p.id}/authorise/")
        self.assertEqual(resp.status_code, 200, resp.content)
        p.refresh_from_db()
        self.assertEqual(p.status, "paid")
        self.assertIsNotNone(p.paid_at)

    def test_non_admin_cannot_authorise(self):
        p = self._pending()
        self.client.force_authenticate(self.user)
        resp = self.client.post(f"/api/payments/{p.id}/authorise/")
        self.assertEqual(resp.status_code, 403)
        p.refresh_from_db()
        self.assertEqual(p.status, "pending")

    def test_admin_pending_list(self):
        self._pending()
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/payments/pending/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(resp.json()["data"]), 1)

    def test_pending_list_forbidden_for_user(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get("/api/payments/pending/")
        self.assertEqual(resp.status_code, 403)

    def test_cannot_authorise_already_paid(self):
        p = self._pending()
        p.status = "paid"
        p.save(update_fields=["status"])
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f"/api/payments/{p.id}/authorise/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["status"], "paid")
