from django.contrib import admin
from .models import UsageRecord

@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "api_requests", "projects_count", "storage_used_gb", "period_start", "period_end"]
    list_filter = ["plan", "period_start", "period_end"]
    search_fields = ["user__username", "user__email"]
    ordering = ["-period_start"]
    date_hierarchy = "period_start"
    readonly_fields = ["created_at", "updated_at"]