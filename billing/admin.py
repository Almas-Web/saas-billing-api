from django.contrib import admin
from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "subscription", "payment", "amount", "currency", "status", "invoice_date", "paid_at"]
    list_filter = ["status", "currency", "invoice_date"]
    search_fields = ["user__username", "user__email", "stripe_invoice_id"]
    readonly_fields = ["invoice_date", "created_at", "updated_at"]