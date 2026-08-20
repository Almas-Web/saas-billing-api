from decimal import Decimal
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import UsageRecord
class UsageRecordSerializer(serializers.ModelSerializer):
    current_plan = serializers.SerializerMethodField()
    api_requests_limit = serializers.SerializerMethodField()
    api_requests_remaining = serializers.SerializerMethodField()
    api_requests_percentage = serializers.SerializerMethodField()
    projects_limit = serializers.SerializerMethodField()
    projects_remaining = serializers.SerializerMethodField()
    projects_percentage = serializers.SerializerMethodField()
    storage_limit_gb = serializers.SerializerMethodField()
    storage_remaining_gb = serializers.SerializerMethodField()
    storage_percentage = serializers.SerializerMethodField()
    api_limit_status = serializers.SerializerMethodField()
    project_limit_status = serializers.SerializerMethodField()
    storage_limit_status = serializers.SerializerMethodField()
    class Meta:
        model = UsageRecord
        fields = ["id", "user", "plan", "current_plan", "api_requests", "api_requests_limit", "api_requests_remaining", "api_requests_percentage", "projects_count", "projects_limit", "projects_remaining", "projects_percentage", "storage_used_gb", "storage_limit_gb", "storage_remaining_gb", "storage_percentage", "api_limit_status", "project_limit_status", "storage_limit_status", "period_start", "period_end", "created_at", "updated_at"]
        read_only_fields = fields
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_current_plan(self, obj):
        return obj.plan.name if obj.plan else None
    @extend_schema_field(serializers.IntegerField())
    def get_api_requests_limit(self, obj):
        return obj.plan.max_api_requests if obj.plan else 0
    @extend_schema_field(serializers.IntegerField())
    def get_api_requests_remaining(self, obj):
        if not obj.plan:
            return 0
        return max(0, obj.plan.max_api_requests - obj.api_requests)
    @extend_schema_field(serializers.FloatField())
    def get_api_requests_percentage(self, obj):
        if not obj.plan or obj.plan.max_api_requests == 0:
            return 0
        percentage = (Decimal(obj.api_requests) / Decimal(obj.plan.max_api_requests)) * 100
        return round(min(percentage, Decimal("100")), 2)
    @extend_schema_field(serializers.IntegerField())
    def get_projects_limit(self, obj):
        return obj.plan.max_projects if obj.plan else 0
    @extend_schema_field(serializers.IntegerField())
    def get_projects_remaining(self, obj):
        if not obj.plan:
            return 0
        return max(0, obj.plan.max_projects - obj.projects_count)
    @extend_schema_field(serializers.FloatField())
    def get_projects_percentage(self, obj):
        if not obj.plan or obj.plan.max_projects == 0:
            return 0
        percentage = (Decimal(obj.projects_count) / Decimal(obj.plan.max_projects)) * 100
        return round(min(percentage, Decimal("100")), 2)
    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_storage_limit_gb(self, obj):
        return obj.plan.storage_limit_gb if obj.plan else Decimal("0.00")
    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_storage_remaining_gb(self, obj):
        if not obj.plan:
            return Decimal("0.00")
        remaining = Decimal(str(obj.plan.storage_limit_gb)) - obj.storage_used_gb
        return max(Decimal("0.00"), remaining)
    @extend_schema_field(serializers.FloatField())
    def get_storage_percentage(self, obj):
        if not obj.plan or obj.plan.storage_limit_gb == 0:
            return 0
        percentage = (obj.storage_used_gb / Decimal(str(obj.plan.storage_limit_gb))) * 100
        return round(min(percentage, Decimal("100")), 2)
    @extend_schema_field(serializers.ChoiceField(choices=["NO_SUBSCRIPTION", "LIMIT_REACHED", "AVAILABLE"]))
    def get_api_limit_status(self, obj):
        if not obj.plan:
            return "NO_SUBSCRIPTION"
        if obj.api_requests >= obj.plan.max_api_requests:
            return "LIMIT_REACHED"
        return "AVAILABLE"
    @extend_schema_field(serializers.ChoiceField(choices=["NO_SUBSCRIPTION", "LIMIT_REACHED", "AVAILABLE"]))
    def get_project_limit_status(self, obj):
        if not obj.plan:
            return "NO_SUBSCRIPTION"
        if obj.projects_count >= obj.plan.max_projects:
            return "LIMIT_REACHED"
        return "AVAILABLE"
    @extend_schema_field(serializers.ChoiceField(choices=["NO_SUBSCRIPTION", "LIMIT_REACHED", "AVAILABLE"]))
    def get_storage_limit_status(self, obj):
        if not obj.plan:
            return "NO_SUBSCRIPTION"
        if obj.storage_used_gb >= obj.plan.storage_limit_gb:
            return "LIMIT_REACHED"
        return "AVAILABLE"