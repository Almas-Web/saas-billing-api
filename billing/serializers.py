from rest_framework import serializers
from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "user", "subscription", "payment", "stripe_invoice_id", "amount", "currency", "status", "invoice_date", "due_date", "paid_at", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "stripe_invoice_id", "status", "invoice_date", "paid_at", "created_at", "updated_at"]
        