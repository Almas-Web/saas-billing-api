from django.contrib import admin
from .models import Plan, Subscription
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "billing_cycle", "max_projects",
                    "max_api_requests", "storage_limit_gb", "is_active"]
    list_filter = ["billing_cycle", "is_active"]
    search_fields = ["name"]

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "start_date", "end_date"]
    list_filter = ["status", "plan"]
    search_fields = ["user__username", "user__email"]