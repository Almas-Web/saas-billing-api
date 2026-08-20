from rest_framework import serializers
from .models import Payment, WebhookEvent

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "user", "subscription", "gateway", "transaction_id", "stripe_payment_intent_id", "amount", "currency", "status", "paid_at", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "transaction_id", "stripe_payment_intent_id", "status", "paid_at", "created_at", "updated_at"]

    def validate_subscription(self, value):
        user = self.context["request"].user
        if value.user != user:
            raise serializers.ValidationError("You can only make payments for your own subscription.")
        if value.status not in ["active", "past_due"]:
            raise serializers.ValidationError("Payment can only be made for an active or past_due subscription.")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value

    def validate_currency(self, value):
        value = value.lower().strip()
        if value not in {"usd", "bdt"}:
            raise serializers.ValidationError("Unsupported currency.")
        return value

    def validate(self, attrs):
        gateway = attrs.get("gateway", "stripe")
        subscription = attrs.get("subscription")
        currency = attrs.get("currency", "usd").lower()
        if subscription and attrs.get("amount") != subscription.plan.price:
            raise serializers.ValidationError({"amount": "Payment amount must match the subscription plan price."})
        if gateway == "stripe" and currency != "usd":
            raise serializers.ValidationError({"currency": "Stripe payments currently require USD."})
        if gateway in ["sslcommerz", "bkash", "nagad"] and currency != "bdt":
            raise serializers.ValidationError({"currency": f"{gateway} payments currently require BDT."})
        return attrs

class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["status"]

    def validate_status(self, value):
        if value not in {"pending", "successful", "failed", "refunded"}:
            raise serializers.ValidationError("Invalid payment status.")
        return value

class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = ["id", "event_id", "event_type", "processed", "created_at"]
        read_only_fields = ["id", "processed", "created_at"]