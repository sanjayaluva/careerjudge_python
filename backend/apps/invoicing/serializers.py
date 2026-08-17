"""Serializers for the Invoicing module."""

from rest_framework import serializers

from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "invoice", "description", "quantity", "unit_price", "total"]
        read_only_fields = ["id", "total"]


class InvoiceSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source="creator.full_name", read_only=True, default="")
    creator_role = serializers.CharField(source="creator.role.name", read_only=True, default="")
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, default=""
    )
    items = InvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "creator",
            "creator_name",
            "creator_role",
            "invoice_type",
            "description",
            "amount",
            "currency",
            "status",
            "reviewed_by",
            "reviewed_by_name",
            "review_comment",
            "reviewed_at",
            "paid_at",
            "payment_reference",
            "task",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reviewed_by",
            "reviewed_at",
            "paid_at",
            "created_at",
            "updated_at",
        ]
