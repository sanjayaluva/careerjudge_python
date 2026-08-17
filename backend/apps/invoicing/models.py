"""Models for the Invoicing module.

Per Doc 4: SME, Reviewer, Trainer, Counsellor, Channel Partner
can create/revise/cancel invoices and send to CJ Admin for payment.
CJ Admin views invoices, approves, and initiates payment.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Invoice(models.Model):
    """An invoice from an empanelled user (SME/Reviewer/Trainer/Counsellor/
    Channel Partner) to CJ Admin for payment.

    Lifecycle:
      draft → submitted → approved → paid
                        → rejected
      submitted → cancelled (by creator)
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted (awaiting CJ Admin review)"),
        ("approved", "Approved (payment initiated)"),
        ("rejected", "Rejected by CJ Admin"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled by creator"),
    ]

    INVOICE_TYPE_CHOICES = [
        ("question_creation", "Question Creation"),
        ("question_review", "Question Review"),
        ("psychometric_review", "Psychometric Review"),
        ("training", "Training Services"),
        ("counseling", "Counseling Services"),
        ("channel_partner", "Channel Partner Commission"),
        ("other", "Other"),
    ]

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_invoices",
    )
    invoice_number = models.CharField(
        _("invoice number"),
        max_length=50,
        unique=True,
        help_text=_("Auto-generated: INV-YYYY-NNNN"),
    )
    invoice_type = models.CharField(
        _("invoice type"), max_length=30, choices=INVOICE_TYPE_CHOICES, default="other"
    )
    description = models.TextField(_("description"), help_text=_("What this invoice is for"))
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    currency = models.CharField(_("currency"), max_length=3, default="INR")

    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="draft")

    # CJ Admin review fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_invoices",
    )
    review_comment = models.TextField(_("review comment"), blank=True, default="")
    reviewed_at = models.DateTimeField(_("reviewed at"), null=True, blank=True)
    paid_at = models.DateTimeField(_("paid at"), null=True, blank=True)
    payment_reference = models.CharField(
        _("payment reference"), max_length=100, blank=True, default=""
    )

    # Optional link to task (for SME/Reviewer invoices)
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        help_text=_("If this invoice is for a specific task"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")
        indexes = [
            models.Index(fields=["creator", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number}: {self.creator.email} — {self.amount} {self.currency} ({self.status})"


class InvoiceItem(models.Model):
    """Line items on an invoice (for detailed breakdown)."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.TextField(_("description"))
    quantity = models.PositiveIntegerField(_("quantity"), default=1)
    unit_price = models.DecimalField(_("unit price"), max_digits=10, decimal_places=2)
    total = models.DecimalField(_("total"), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _("invoice item")
        verbose_name_plural = _("invoice items")

    def __str__(self) -> str:
        return f"{self.invoice.invoice_number} — {self.description[:50]}"

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
