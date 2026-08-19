from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "created_at",
        "updated_at",
    )
    search_fields = (
        "name",
        "description",
        "user__username",
        "user__email",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )