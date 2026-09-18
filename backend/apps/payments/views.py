"""Views for the Payments module.

Endpoints:
  GET   /api/payments/config/              — payment settings (public keys, is configured)
  PATCH /api/payments/config/              — update payment settings (admin only)
  POST  /api/payments/checkout/            — create Stripe checkout session → returns redirect URL
  GET   /api/payments/status/<module>/<item_id>/  — check payment status for an item
  POST  /api/payments/verify/              — verify a Stripe session after redirect
  POST  /api/payments/stripe-webhook/      — Stripe webhook (no auth, signature verified)
  GET   /api/payments/history/             — user's payment history
"""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Payment, PaymentSettings
from .serializers import PaymentSerializer
from .services import (
    _update_module_payment_status,
    create_stripe_checkout_session,
    get_or_create_payment,
    handle_stripe_webhook,
    verify_stripe_payment,
)


def _is_payments_admin(user) -> bool:
    if user.is_superuser:
        return True
    return user.role_id is not None and user.role.name == "cj_admin"


class PaymentViewSet(ModelViewSet):
    """Payment CRUD + checkout + verification."""

    queryset = Payment.objects.select_related("user")
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    http_method_names = ["get", "head", "options", "post"]

    def get_queryset(self):
        user = self.request.user
        user_role = user.role.name if user.role_id else None
        if user_role == "cj_admin":
            return super().get_queryset()
        return super().get_queryset().filter(user=user)

    @action(detail=False, methods=["get"])
    def config(self, request):
        """Get payment configuration (public keys, whether Stripe is configured)."""
        settings = PaymentSettings.get()
        return Response(
            {
                "message": "OK",
                "data": {
                    "active_provider": settings.active_provider,
                    "is_active": settings.is_active,
                    "is_stripe_configured": settings.is_stripe_configured,
                    "is_razorpay_configured": settings.is_razorpay_configured,
                    "stripe_publishable_key": (
                        settings.stripe_publishable_key if settings.is_stripe_configured else ""
                    ),
                    "currency": settings.currency,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """Create a Stripe Checkout Session for a paid item.

        Body:
            {
                "module": "training" | "counseling" | ...,
                "item_id": 42,
                "amount": "99.99",
                "description": "Python 101 Course Registration"
            }

        Returns:
            { "checkout_url": "https://checkout.stripe.com/..." }
            or
            { "status": "free" } if amount is 0
            or
            { "status": "manual" } if Stripe is not configured
        """
        module = request.data.get("module")
        item_id = request.data.get("item_id")
        amount = request.data.get("amount", "0")
        description = request.data.get("description", "")

        if not module or not item_id:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "module and item_id are required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create payment record
        payment = get_or_create_payment(
            user=request.user,
            module=module,
            item_id=int(item_id),
            amount=amount,
            description=description,
        )

        # Free items — no checkout needed
        if payment.status == "free":
            return Response(
                {"message": "Free item — no payment required.", "data": {"status": "free"}},
                status=status.HTTP_200_OK,
            )

        # Already paid
        if payment.is_paid:
            return Response(
                {"message": "Already paid.", "data": {"status": "paid"}},
                status=status.HTTP_200_OK,
            )

        # Try Stripe checkout
        frontend_url = request.build_absolute_uri("/").rstrip("/")
        success_url = f"{frontend_url}/payments/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/payments/cancel"

        checkout_url = create_stripe_checkout_session(payment, success_url, cancel_url)

        if checkout_url:
            return Response(
                {"message": "Redirect to Stripe.", "data": {"checkout_url": checkout_url}},
                status=status.HTTP_200_OK,
            )

        # Stripe not configured — manual processing
        return Response(
            {
                "message": "Payment gateway not configured. Payment is pending manual processing.",
                "data": {"status": "manual"},
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="status/(?P<module>[^/]+)/(?P<item_id>[^/]+)")
    def payment_status(self, request, module=None, item_id=None):
        """Check payment status for a specific item."""
        payment = Payment.objects.filter(
            user=request.user, module=module, item_id=int(item_id)
        ).first()

        if not payment:
            return Response(
                {"message": "OK", "data": {"status": "none", "is_paid": False}},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "message": "OK",
                "data": {
                    "status": payment.status,
                    "is_paid": payment.is_paid,
                    "amount": str(payment.amount),
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def verify(self, request):
        """Verify a Stripe checkout session after the user is redirected back.

        Body: { "session_id": "cs_test_..." }
        """
        session_id = request.data.get("session_id")
        if not session_id:
            return Response(
                {"error": {"code": "validation_error", "message": "session_id is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success = verify_stripe_payment(session_id)
        if success:
            return Response(
                {"message": "Payment verified successfully.", "data": {"status": "paid"}},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"message": "Payment verification pending.", "data": {"status": "pending"}},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def history(self, request):
        """User's payment history."""
        payments = self.get_queryset().order_by("-created_at")
        return Response(
            {"message": "OK", "data": PaymentSerializer(payments, many=True).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Admin payment-authorise workflow (E-PLT-2): list payments awaiting
        manual authorisation (e.g. offline / manual-gateway payments)."""
        if not _is_payments_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can view pending payments."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        payments = Payment.objects.filter(status="pending").select_related("user").order_by(
            "-created_at"
        )
        return Response(
            {"message": "OK", "data": PaymentSerializer(payments, many=True).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def authorise(self, request, pk=None):
        """Admin payment-authorise workflow (E-PLT-2): CJ Admin manually
        authorises a pending payment (offline transfer, cash, manual gateway),
        marking it paid and propagating that to the linked module so the
        candidate/student/counselee gets access."""
        if not _is_payments_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can authorise payments."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        payment = Payment.objects.filter(pk=pk).first()
        if not payment:
            return Response(
                {"error": {"code": "not_found", "message": "Payment not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if payment.status in ("paid", "free"):
            return Response(
                {"message": "Payment already settled.", "data": {"status": payment.status}},
                status=status.HTTP_200_OK,
            )
        if payment.status not in ("pending", "failed"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": f"Cannot authorise a payment in status '{payment.status}'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone

        payment.status = "paid"
        payment.paid_at = timezone.now()
        note = (request.data.get("reference") or "manual-authorisation").strip()
        payment.provider = payment.provider or "manual"
        payment.provider_session_id = payment.provider_session_id or note
        payment.save(update_fields=["status", "paid_at", "provider", "provider_session_id"])
        _update_module_payment_status(payment)
        return Response(
            {"message": "Payment authorised.", "data": PaymentSerializer(payment).data},
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """Stripe webhook endpoint — no auth required, verified by signature.

    Stripe sends events here when payments complete. The webhook secret
    is used to verify the request is genuinely from Stripe.
    """
    payload = request.body
    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    success = handle_stripe_webhook(payload, signature)
    if success:
        return HttpResponse(status=200)
    return HttpResponse(status=400)
