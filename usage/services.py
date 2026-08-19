from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .models import UsageRecord


def get_current_usage(user):
    from projects.models import Project

    now = timezone.now()

    usage = (
        UsageRecord.objects
        .filter(
            user=user,
            period_start__lte=now,
            period_end__gt=now
        )
        .order_by("-period_start")
        .first()
    )

    if usage:
        actual_project_count = Project.objects.filter(user=user).count()

        if usage.projects_count != actual_project_count:
            usage.projects_count = actual_project_count
            usage.save(update_fields=["projects_count", "updated_at"])

        return usage

    subscription = (
        user.subscriptions
        .filter(status="active")
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )

    plan = subscription.plan if subscription else None

    period_start = now.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    if period_start.month == 12:
        period_end = period_start.replace(
            year=period_start.year + 1,
            month=1
        )
    else:
        period_end = period_start.replace(
            month=period_start.month + 1
        )

    projects_count = Project.objects.filter(user=user).count()

    usage = UsageRecord.objects.create(
        user=user,
        plan=plan,
        api_requests=0,
        projects_count=projects_count,
        storage_used_gb=Decimal("0.00"),
        period_start=period_start,
        period_end=period_end
    )

    return usage


def increment_api_requests(user, amount=1):
    usage = get_current_usage(user)

    usage.api_requests += amount

    usage.save(
        update_fields=["api_requests", "updated_at"]
    )

    return usage


def update_projects_count(user, count):
    usage = get_current_usage(user)

    usage.projects_count = count

    usage.save(
        update_fields=["projects_count", "updated_at"]
    )

    return usage


def update_storage_usage(user, storage_gb):
    usage = get_current_usage(user)

    usage.storage_used_gb = Decimal(str(storage_gb))

    usage.save(
        update_fields=["storage_used_gb", "updated_at"]
    )

    return usage


def check_api_request_limit(user):
    usage = get_current_usage(user)

    if not usage.plan:
        raise PermissionDenied("No active subscription found.")

    if usage.api_requests >= usage.plan.max_api_requests:
        raise PermissionDenied("API request limit exceeded.")

    return True


def track_api_request(user):
    check_api_request_limit(user)

    usage = get_current_usage(user)

    usage.api_requests += 1

    usage.save(
        update_fields=["api_requests", "updated_at"]
    )

    return usage


def check_project_limit(user):
    usage = get_current_usage(user)

    if not usage.plan:
        raise PermissionDenied("No active subscription found.")

    if usage.projects_count >= usage.plan.max_projects:
        raise PermissionDenied("Project limit exceeded.")

    return True


def increment_projects_count(user, amount=1):
    usage = get_current_usage(user)

    usage.projects_count += amount

    usage.save(
        update_fields=["projects_count", "updated_at"]
    )

    return usage


def decrement_projects_count(user, amount=1):
    usage = get_current_usage(user)

    usage.projects_count = max(
        0,
        usage.projects_count - amount
    )

    usage.save(
        update_fields=["projects_count", "updated_at"]
    )

    return usage


def check_storage_limit(user, additional_storage_gb=0):
    usage = get_current_usage(user)

    if not usage.plan:
        raise PermissionDenied("No active subscription found.")

    new_usage = (
        usage.storage_used_gb
        + Decimal(str(additional_storage_gb))
    )

    if new_usage > usage.plan.storage_limit_gb:
        raise PermissionDenied("Storage limit exceeded.")

    return True


def add_storage_usage(user, storage_gb):
    check_storage_limit(user, storage_gb)

    usage = get_current_usage(user)

    usage.storage_used_gb += Decimal(str(storage_gb))

    usage.save(
        update_fields=["storage_used_gb", "updated_at"]
    )

    return usage