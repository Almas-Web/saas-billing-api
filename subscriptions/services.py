from calendar import monthrange
from datetime import timedelta

from django.utils import timezone


def add_months(date, months=1):
    """
    Safely add months to a date/datetime.
    Handles month-end dates such as January 31.
    """
    month = date.month - 1 + months
    year = date.year + month // 12
    month = month % 12 + 1

    day = min(
        date.day,
        monthrange(year, month)[1],
    )

    return date.replace(
        year=year,
        month=month,
        day=day,
    )


def calculate_subscription_end_date(subscription, start_date=None):
    """
    Calculate subscription end date based on plan billing cycle.
    """

    if start_date is None:
        start_date = timezone.now()

    if subscription.plan.billing_cycle == "monthly":
        return add_months(start_date, 1)

    if subscription.plan.billing_cycle == "yearly":
        return add_months(start_date, 12)

    raise ValueError(
        f"Unsupported billing cycle: {subscription.plan.billing_cycle}"
    )


def activate_or_renew_subscription(subscription):
    """
    Activate a subscription for the first time or renew its billing period.
    """

    now = timezone.now()

    if (
        subscription.end_date
        and subscription.end_date > now
        and subscription.status == "active"
    ):
        # Existing active subscription:
        # extend from current end date.
        new_end_date = calculate_subscription_end_date(
            subscription,
            start_date=subscription.end_date,
        )
    else:
        # New, expired, canceled, or past-due subscription:
        # start a fresh billing period from now.
        subscription.start_date = now

        new_end_date = calculate_subscription_end_date(
            subscription,
            start_date=now,
        )

    subscription.status = "active"
    subscription.end_date = new_end_date

    subscription.save(
        update_fields=[
            "status",
            "start_date",
            "end_date",
            "updated_at",
        ]
    )

    return subscription