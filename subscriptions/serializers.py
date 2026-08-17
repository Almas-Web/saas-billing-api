from rest_framework import serializers
from .models import Plan, Subscription

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "price", "billing_cycle", "max_projects",
                  "max_api_requests", "storage_limit_gb", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ["id", "plan", "status", "stripe_subscription_id",
                  "start_date", "end_date", "created_at", "updated_at"]
        read_only_fields = ["id", "stripe_subscription_id", "start_date",
                            "end_date", "created_at", "updated_at"]

class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()

    def validate_plan_id(self, value):
        try:
            plan = Plan.objects.get(id=value, is_active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Plan not found.")

        return plan