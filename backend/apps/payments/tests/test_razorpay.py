"""E-PLT-4: Razorpay verification + webhook (signature via stdlib HMAC)."""

import hashlib
import hmac
import json
from decimal import Decimal

import pytest

from apps.accounts.models import Role, User
from apps.payments.models import Payment, PaymentSettings
from apps.payments.services import (
    handle_razorpay_webhook,
    verify_razorpay_payment,
)

pytestmark = pytest.mark.django_db

SECRET = "rzp_secret_test"


def _configure_razorpay():
    s = PaymentSettings.get()
    s.active_provider = "razorpay"
    s.razorpay_key_id = "rzp_key_test"
    s.razorpay_key_secret = SECRET
    s.razorpay_webhook_secret = SECRET
    s.save()
    return s


def _user():
    role, _ = Role.objects.get_or_create(name="individual", defaults={"is_system": True})
    return User.objects.create_user(email="rzp@test.com", password="pw12345", role=role)


def _sign(message: str, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def test_verify_razorpay_payment_marks_paid():
    _configure_razorpay()
    user = _user()
    payment = Payment.objects.create(
        user=user, module="assessment", item_id=7, amount=Decimal("25.00"),
        status="pending", provider="razorpay", provider_session_id="order_ABC",
    )
    sig = _sign("order_ABC|pay_XYZ")
    assert verify_razorpay_payment("order_ABC", "pay_XYZ", sig) is True
    payment.refresh_from_db()
    assert payment.status == "paid"
    assert payment.paid_at is not None


def test_verify_razorpay_payment_rejects_bad_signature():
    _configure_razorpay()
    user = _user()
    payment = Payment.objects.create(
        user=user, module="assessment", item_id=7, amount=Decimal("25.00"),
        status="pending", provider="razorpay", provider_session_id="order_ABC",
    )
    assert verify_razorpay_payment("order_ABC", "pay_XYZ", "deadbeef") is False
    payment.refresh_from_db()
    assert payment.status == "pending"


def test_razorpay_webhook_marks_paid():
    _configure_razorpay()
    user = _user()
    payment = Payment.objects.create(
        user=user, module="assessment", item_id=7, amount=Decimal("25.00"),
        status="pending", provider="razorpay", provider_session_id="order_WH",
    )
    body = json.dumps(
        {"payload": {"payment": {"entity": {"order_id": "order_WH"}}}}
    ).encode()
    sig = _sign(body.decode())
    assert handle_razorpay_webhook(body, sig) is True
    payment.refresh_from_db()
    assert payment.status == "paid"


def test_razorpay_webhook_rejects_bad_signature():
    _configure_razorpay()
    body = json.dumps({"payload": {}}).encode()
    assert handle_razorpay_webhook(body, "bad") is False


def test_verify_returns_false_when_not_configured():
    # No razorpay keys set.
    assert verify_razorpay_payment("o", "p", "s") is False
