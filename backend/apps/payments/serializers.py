"""Serializers for the Payments module."""

from rest_framework import serializers

from .models import Payment, PaymentSettings


class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "user_email",
            "module",
            "item_id",
            "amount",
            "currency",
            "status",
            "provider",
            "provider_session_id",
            "description",
            "created_at",
            "paid_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_email",
            "provider_session_id",
            "created_at",
            "paid_at",
        ]


class PaymentSettingsSerializer(serializers.ModelSerializer):
    is_stripe_configured = serializers.BooleanField(read_only=True)
    is_razorpay_configured = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaymentSettings
        fields = [
            "active_provider",
            "stripe_publishable_key",
            "is_stripe_configured",
            "is_razorpay_configured",
            "currency",
            "is_active",
        ]
        # Secret keys are write-only (never returned to frontend)
        extra_kwargs = {
            "stripe_secret_key": {"write_only": True},
            "stripe_webhook_secret": {"write_only": True},
            "razorpay_key_secret": {"write_only": True},
        }
