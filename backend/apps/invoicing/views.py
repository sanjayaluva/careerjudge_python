"""Views for the Invoicing module.

Endpoints:
  GET/POST   /api/invoicing/invoices/             — list/create invoices
  GET/PATCH  /api/invoicing/invoices/<id>/         — retrieve/update
  POST       /api/invoicing/invoices/<id>/submit/  — submit to CJ Admin
  POST       /api/invoicing/invoices/<id>/cancel/  — cancel by creator
  POST       /api/invoicing/invoices/<id>/approve/ — CJ Admin approves
  POST       /api/invoicing/invoices/<id>/reject/  — CJ Admin rejects
  POST       /api/invoicing/invoices/<id>/pay/     — CJ Admin marks paid
  GET        /api/invoicing/invoices/my-invoices/  — creator's own invoices
  GET        /api/invoicing/invoices/pending/      — CJ Admin: pending review
"""

import uuid
from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Invoice
from .serializers import InvoiceSerializer


def _is_admin(user) -> bool:
    if user.is_superuser:
        return True
    return user.role_id is not None and user.role.name == "cj_admin"


# H14: only the empanelled roles that actually bill CJ Admin for their work
# (Doc 4) — plus cj_admin itself (e.g. raising an invoice on someone's
# behalf) — may create invoices. Everyone else (individual, corp_admin,
# helpdesk, ...) has no reason to invoice CareerJudge.
EMPANELLED_ROLES = {
    "sme",
    "reviewer",
    "trainer",
    "counsellor",
    "channel_partner",
    "psychometrician",
}


def _can_create_invoice(user) -> bool:
    if _is_admin(user):
        return True
    return user.role_id is not None and user.role.name in EMPANELLED_ROLES


def _generate_invoice_number() -> str:
    """Generate a unique invoice number: INV-YYYY-NNNN."""
    year = datetime.now().year
    suffix = uuid.uuid4().hex[:6].upper()
    return f"INV-{year}-{suffix}"


class InvoiceViewSet(ModelViewSet):
    """Invoice CRUD + submit/cancel/approve/reject/pay."""

    queryset = Invoice.objects.select_related("creator", "reviewed_by", "task")
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if _is_admin(user):
            return super().get_queryset()
        # Non-admins see only their own invoices
        return super().get_queryset().filter(creator=user)

    def create(self, request, *args, **kwargs):
        if not _can_create_invoice(request.user):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": (
                            "Only empanelled roles (SME, Reviewer, Trainer, Counsellor, "
                            "Channel Partner, Psychometrician) or CJ Admin can create invoices."
                        ),
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        data = request.data.copy()
        data["creator"] = request.user.id
        data["invoice_number"] = _generate_invoice_number()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Invoice created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Creator submits invoice to CJ Admin for review."""
        invoice = self.get_object()
        if invoice.creator_id != request.user.id:
            return Response(
                {"error": {"code": "forbidden", "message": "Not your invoice."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if invoice.status != "draft":
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": f"Cannot submit invoice in status '{invoice.status}'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = "submitted"
        invoice.save(update_fields=["status"])
        # Notify CJ Admin
        from apps.notifications.models import notify_role

        notify_role(
            "cj_admin",
            "New invoice submitted",
            f"Invoice {invoice.invoice_number} from {request.user.email} for {invoice.amount} {invoice.currency}.",
            "info",
            f"/invoicing/{invoice.id}",
        )
        return Response(
            {"message": "Invoice submitted to CJ Admin.", "data": InvoiceSerializer(invoice).data}
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Creator cancels an invoice."""
        invoice = self.get_object()
        if invoice.creator_id != request.user.id:
            return Response(
                {"error": {"code": "forbidden", "message": "Not your invoice."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if invoice.status in ("paid", "cancelled"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": f"Cannot cancel invoice in status '{invoice.status}'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = "cancelled"
        invoice.save(update_fields=["status"])
        return Response({"message": "Invoice cancelled.", "data": InvoiceSerializer(invoice).data})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """CJ Admin approves an invoice (payment initiated)."""
        invoice = self.get_object()
        if not _is_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can approve."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if invoice.status != "submitted":
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": f"Cannot approve invoice in status '{invoice.status}'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        comment = request.data.get("comment", "")
        invoice.status = "approved"
        invoice.reviewed_by = request.user
        invoice.review_comment = comment
        invoice.reviewed_at = timezone.now()
        invoice.save(update_fields=["status", "reviewed_by", "review_comment", "reviewed_at"])
        # Notify creator
        from apps.notifications.models import notify_user

        notify_user(
            invoice.creator,
            "Invoice approved",
            f"Your invoice {invoice.invoice_number} has been approved. Payment will be initiated.",
            "success",
            f"/invoicing/{invoice.id}",
        )
        return Response({"message": "Invoice approved.", "data": InvoiceSerializer(invoice).data})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """CJ Admin rejects an invoice."""
        invoice = self.get_object()
        if not _is_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can reject."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        comment = request.data.get("comment", "")
        invoice.status = "rejected"
        invoice.reviewed_by = request.user
        invoice.review_comment = comment
        invoice.reviewed_at = timezone.now()
        invoice.save(update_fields=["status", "reviewed_by", "review_comment", "reviewed_at"])
        from apps.notifications.models import notify_user

        notify_user(
            invoice.creator,
            "Invoice rejected",
            f"Your invoice {invoice.invoice_number} was rejected. Comment: {comment}",
            "warning",
            f"/invoicing/{invoice.id}",
        )
        return Response({"message": "Invoice rejected.", "data": InvoiceSerializer(invoice).data})

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        """CJ Admin marks invoice as paid."""
        invoice = self.get_object()
        if not _is_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can mark as paid."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if invoice.status != "approved":
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": f"Cannot pay invoice in status '{invoice.status}'.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment_ref = request.data.get("payment_reference", "")
        invoice.status = "paid"
        invoice.paid_at = timezone.now()
        invoice.payment_reference = payment_ref
        invoice.save(update_fields=["status", "paid_at", "payment_reference"])
        from apps.notifications.models import notify_user

        notify_user(
            invoice.creator,
            "Invoice paid",
            f"Your invoice {invoice.invoice_number} has been paid. Reference: {payment_ref}",
            "success",
            f"/invoicing/{invoice.id}",
        )
        return Response(
            {"message": "Invoice marked as paid.", "data": InvoiceSerializer(invoice).data}
        )

    @action(detail=False, methods=["get"])
    def my_invoices(self, request):
        """Creator's own invoices."""
        qs = self.get_queryset().filter(creator=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response({"message": "OK", "data": InvoiceSerializer(qs, many=True).data})

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """CJ Admin: invoices pending review."""
        if not _is_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can view pending."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = self.get_queryset().filter(status="submitted")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response({"message": "OK", "data": InvoiceSerializer(qs, many=True).data})
