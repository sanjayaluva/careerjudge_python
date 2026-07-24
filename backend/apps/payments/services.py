"""Payment service — creates Stripe Checkout sessions and verifies payments."""

import logging

from django.utils import timezone

from .models import Payment, PaymentSettings

logger = logging.getLogger(__name__)


def get_or_create_payment(
    user, module: str, item_id: int, amount, description: str = ""
) -> Payment:
    """Get or create a payment record for a payable item.

    For free items (amount == 0), auto-marks as 'free' (no payment needed).
    For paid items, creates a 'pending' payment.
    """
    payment, created = Payment.objects.get_or_create(
        user=user,
        module=module,
        item_id=item_id,
        defaults={
            "amount": amount,
            "description": description,
            "status": "free" if float(amount) == 0 else "pending",
            "provider": "free" if float(amount) == 0 else "stripe",
        },
    )
    return payment


def create_stripe_checkout_session(
    payment: Payment, success_url: str, cancel_url: str
) -> str | None:
    """Create a Stripe Checkout Session and return the redirect URL.

    Returns None if Stripe is not configured. The caller should fall back
    to manual payment processing in that case.
    """
    settings = PaymentSettings.get()
    if not settings.is_stripe_configured:
        logger.info("Stripe not configured — payment stays pending for manual processing.")
        return None

    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": settings.currency.lower(),
                        "product_data": {
                            "name": payment.description or f"{payment.module}#{payment.item_id}",
                        },
                        "unit_amount": int(float(payment.amount) * 100),  # cents
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "payment_id": str(payment.id),
                "user_id": str(payment.user_id),
                "module": payment.module,
                "item_id": str(payment.item_id),
            },
        )

        payment.provider_session_id = session.id
        payment.provider = "stripe"
        payment.save(update_fields=["provider_session_id", "provider"])

        return session.url
    except Exception as e:
        logger.error("Stripe checkout session creation failed: %s", e)
        return None


def verify_stripe_payment(session_id: str) -> bool:
    """Verify a Stripe Checkout Session and mark the payment as paid."""
    settings = PaymentSettings.get()
    if not settings.is_stripe_configured:
        return False

    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == "paid":
            payment = Payment.objects.filter(provider_session_id=session_id).first()
            if payment and payment.status != "paid":
                payment.status = "paid"
                payment.paid_at = timezone.now()
                payment.save(update_fields=["status", "paid_at"])

                # Update the linked module's payment status
                _update_module_payment_status(payment)
            return True
    except Exception as e:
        logger.error("Stripe payment verification failed: %s", e)
    return False


def handle_stripe_webhook(payload: bytes, signature: str) -> bool:
    """Handle a Stripe webhook event."""
    settings = PaymentSettings.get()
    if not settings.is_stripe_configured or not settings.stripe_webhook_secret:
        return False

    try:
        import stripe

        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            payment = Payment.objects.filter(provider_session_id=session["id"]).first()
            if payment:
                payment.status = "paid"
                payment.paid_at = timezone.now()
                payment.save(update_fields=["status", "paid_at"])
                _update_module_payment_status(payment)
                logger.info("Payment #%d marked as paid via webhook.", payment.id)

        return True
    except Exception as e:
        logger.error("Stripe webhook handling failed: %s", e)
        return False


def _update_module_payment_status(payment: Payment):
    """Update the linked module's payment status after a successful payment."""
    if payment.module == "training":
        from apps.training.models import CourseRegistration

        reg = CourseRegistration.objects.filter(
            course_id=payment.item_id, student=payment.user
        ).first()
        if reg:
            reg.payment_status = "paid"
            reg.completion_status = "in_progress"
            reg.save(update_fields=["payment_status", "completion_status"])

    elif payment.module == "counseling":
        from apps.counseling.models import CounselingSession

        session = CounselingSession.objects.filter(
            id=payment.item_id, counselee=payment.user
        ).first()
        if session:
            session.payment_status = "paid"
            session.save(update_fields=["payment_status"])
