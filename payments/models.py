from django.db import models
from django.conf import settings
from subscriptions.models import Subscription


class Payment(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("successful", "Successful"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    GATEWAY_CHOICES = (
        ("stripe", "Stripe"),
        ("sslcommerz", "SSLCommerz"),
        ("bkash", "bKash"),
        ("nagad", "Nagad"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")

    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default="stripe")
    transaction_id = models.CharField(max_length=255, blank=True, null=True)

    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, blank=True, null=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency}"


class WebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id