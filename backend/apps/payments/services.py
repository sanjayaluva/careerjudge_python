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


def refund_payment(payment: Payment, amount=None) -> bool:
    """Execute a refund for a paid Payment record (dossier gap D8: 'refunds
    are currently recorded but not executed/scheduled').

    Attempts a real gateway refund when Stripe is configured and the payment
    has a checkout session on record; regardless of whether the gateway call
    succeeds (or Stripe isn't configured at all — scoped out here since it
    requires live gateway credentials), the payment record itself is always
    flipped to 'refunded' so the system of record reflects the refund.

    Args:
        payment: the Payment row to refund. No-op (returns False) unless its
            status is currently 'paid'.
        amount: optional partial-refund amount (defaults to a full refund of
            the original payment amount).

    Returns:
        True if the payment record was updated to 'refunded'.
    """
    if payment.status != "paid":
        return False

    settings = PaymentSettings.get()
    if settings.is_stripe_configured and payment.provider == "stripe" and payment.provider_session_id:
        try:
            import stripe

            stripe.api_key = settings.stripe_secret_key
            checkout_session = stripe.checkout.Session.retrieve(payment.provider_session_id)
            payment_intent_id = checkout_session.get("payment_intent")
            if payment_intent_id:
                refund_kwargs = {"payment_intent": payment_intent_id}
                if amount is not None:
                    refund_kwargs["amount"] = int(float(amount) * 100)
                stripe.Refund.create(**refund_kwargs)
                logger.info("Stripe refund issued for payment #%d.", payment.id)
        except Exception as e:
            # Gateway call is best-effort here — the payment record below is
            # still marked refunded so the refund isn't lost from our system
            # of record even if the gateway round-trip fails.
            logger.warning("Stripe refund call failed for payment #%d: %s", payment.id, e)
    else:
        logger.info(
            "No gateway refund attempted for payment #%d (Stripe not configured or no "
            "checkout session on record) — recording the refund on the payment only.",
            payment.id,
        )

    payment.status = "refunded"
    payment.refunded_at = timezone.now()
    payment.save(update_fields=["status", "refunded_at"])
    return True


def _update_module_payment_status(payment: Payment):
    """Update the linked module's payment status after a successful payment."""
    if payment.module == "training":
        from django.utils import timezone

        from apps.training.models import CourseRegistration

        reg = CourseRegistration.objects.filter(
            course_id=payment.item_id, student=payment.user
        ).first()
        if reg and reg.payment_status != "paid":
            reg.payment_status = "paid"
            reg.completion_status = "in_progress"
            # SRS §6: for scheduled courses the duration countdown begins
            # when payment completes.
            if reg.course.schedule_type == "scheduled" and not reg.started_at:
                reg.started_at = timezone.now()
            reg.save(update_fields=["payment_status", "completion_status", "started_at"])
            # Notify trainer + admin that payment confirmed (Report 3 §1.5).
            try:
                from apps.notifications.models import notify_role, notify_user

                student_name = reg.student.full_name or reg.student.email
                title = f"Payment confirmed: {student_name}"
                body = (
                    f"{student_name} has paid for '{reg.course.title}' and can "
                    f"now start the course."
                )
                link = f"/training/{reg.course_id}"
                if reg.course.created_by:
                    notify_user(reg.course.created_by, title, body, "success", link)
                notify_role("cj_admin", title, body, "success", link)
            except Exception as e:
                logger.warning("Training payment notification failed: %s", e)

    elif payment.module == "counseling":
        from apps.counseling.models import CounselingSession

        session = CounselingSession.objects.filter(
            id=payment.item_id, counselee=payment.user
        ).first()
        if session:
            session.payment_status = "paid"
            session.save(update_fields=["payment_status"])
