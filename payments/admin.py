from django.contrib import admin
from .models import Payment, WebhookEvent
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ( "id", "user", "subscription", "amount", "currency", "status", "paid_at","created_at",)
    list_filter = ("status", "currency")
    search_fields = (  "user__username", "user__email", "stripe_payment_intent_id",)
@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id","event_id","event_type","processed","created_at", )
    list_filter = ("processed", "event_type")
    search_fields = ("event_id", "event_type")