"""Checkout never trusts a price sent by the browser (Report 9 review)."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.assessment.models import Assessment
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


def _client():
    role, _ = Role.objects.get_or_create(name="individual", defaults={"is_system": True})
    user = User.objects.create_user(email="buyer@test.com", password="pw12345", role=role)
    c = APIClient()
    c.force_authenticate(user=user)
    return c, user


def test_checkout_uses_the_assessments_own_price():
    c, user = _client()
    a = Assessment.objects.create(title="Paid", status="published", price=Decimal("500.00"))
    resp = c.post(
        "/api/payments/checkout/",
        {"module": "assessment", "item_id": a.id, "amount": "1.00"},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    payment = Payment.objects.get(user=user, module="assessment", item_id=a.id)
    assert payment.amount == Decimal("500.00")
    assert payment.status == "pending"


def test_checkout_refuses_items_without_a_server_price():
    c, _ = _client()
    resp = c.post(
        "/api/payments/checkout/",
        {"module": "counseling", "item_id": 999, "amount": "0"},
        format="json",
    )
    assert resp.status_code == 400
