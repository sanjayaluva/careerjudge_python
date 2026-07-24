"""Payment models — cross-cutting payment tracking for all modules.

Tracks payments for:
  - Training course registration (module='training', item_id=course_id)
  - Counseling session booking (module='counseling', item_id=session_id)
  - Reports (module='reporting', item_id=report_id)
  - Assessments (module='assessment', item_id=assessment_id)

Uses Stripe Checkout for paid items. If Stripe is not configured
(no API keys in env), payments stay 'pending' for manual processing.
Free items (price=0) are auto-marked as 'paid'.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    """A payment record for any payable item across modules."""

    MODULE_CHOICES = [
        ("training", "Training Course"),
        ("counseling", "Counseling Session"),
        ("assessment", "Assessment"),
        ("reporting", "Report"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending (awaiting payment)"),
        ("paid", "Paid"),
        ("failed", "Payment Failed"),
        ("refunded", "Refunded"),
        ("free", "Free (no payment required)"),
    ]
    PROVIDER_CHOICES = [
        ("razorpay", "Razorpay (Primary)"),
        ("stripe", "Stripe (Optional)"),
        ("paytm", "Paytm (Optional)"),
        ("manual", "Manual (no gateway)"),
        ("free", "Free"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    module = models.CharField(_("module"), max_length=20, choices=MODULE_CHOICES)
    item_id = models.PositiveIntegerField(
        _("item ID"), help_text=_("The ID of the item being paid for")
    )
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    currency = models.CharField(_("currency"), max_length=3, default="USD")

    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="pending")
    provider = models.CharField(
        _("provider"), max_length=20, choices=PROVIDER_CHOICES, default="stripe"
    )

    # Stripe session ID (for checkout sessions)
    provider_session_id = models.CharField(
        _("provider session ID"), max_length=255, blank=True, default=""
    )

    # Description shown on the payment page
    description = models.CharField(_("description"), max_length=500, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(_("paid at"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        unique_together = [("user", "module", "item_id")]

    def __str__(self) -> str:
        return f"{self.user.email} → {self.module}#{self.item_id} ({self.status})"

    @property
    def is_paid(self) -> bool:
        return self.status in ("paid", "free")


class PaymentSettings(models.Model):
    """Singleton model for payment gateway configuration.

    Stores Stripe/Razorpay API keys. If no keys are set, payments
    default to 'manual' mode (admin processes offline).
    """

    PROVIDER_CHOICES = [
        ("razorpay", "Razorpay (Primary)"),
        ("stripe", "Stripe (Optional)"),
        ("paytm", "Paytm (Optional)"),
        ("manual", "Manual (no gateway)"),
    ]

    active_provider = models.CharField(
        _("active provider"), max_length=20, choices=PROVIDER_CHOICES, default="razorpay"
    )

    # Razorpay (Primary)
    razorpay_key_id = models.CharField(_("Razorpay key ID"), max_length=255, blank=True, default="")
    razorpay_key_secret = models.CharField(
        _("Razorpay key secret"), max_length=255, blank=True, default=""
    )
    razorpay_webhook_secret = models.CharField(
        _("Razorpay webhook secret"), max_length=255, blank=True, default=""
    )

    # Stripe (Optional)
    stripe_secret_key = models.CharField(
        _("Stripe secret key"), max_length=255, blank=True, default=""
    )
    stripe_publishable_key = models.CharField(
        _("Stripe publishable key"), max_length=255, blank=True, default=""
    )
    stripe_webhook_secret = models.CharField(
        _("Stripe webhook secret"), max_length=255, blank=True, default=""
    )

    # Paytm (Optional)
    paytm_merchant_id = models.CharField(
        _("Paytm merchant ID"), max_length=255, blank=True, default=""
    )
    paytm_merchant_key = models.CharField(
        _("Paytm merchant key"), max_length=255, blank=True, default=""
    )

    currency = models.CharField(_("currency"), max_length=3, default="USD")
    is_active = models.BooleanField(_("payments enabled"), default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("payment settings")
        verbose_name_plural = _("payment settings")

    def __str__(self) -> str:
        return f"Payment Settings ({self.active_provider})"

    @classmethod
    def get(cls) -> "PaymentSettings":
        """Get or create the singleton settings instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def is_stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_publishable_key)

    @property
    def is_razorpay_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)
