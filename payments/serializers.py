from rest_framework import serializers
from .models import Payment, WebhookEvent

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [  "id",  "user","subscription","stripe_payment_intent_id","amount",
            "currency","status","paid_at","created_at","updated_at",]
        read_only_fields = [ "id", "user","stripe_payment_intent_id","status",
            "paid_at", "created_at", "updated_at",]
class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["status"]

class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = ["id", "event_id", "event_type", "processed", "created_at"]
        read_only_fields = ["id", "processed", "created_at"]