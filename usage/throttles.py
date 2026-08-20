from datetime import timedelta

from django.utils import timezone

from rest_framework.throttling import BaseThrottle

from .models import APIRequestLog


class DatabaseRateThrottle(BaseThrottle):
    rate = 60
    duration = timedelta(minutes=1)

    def allow_request(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True

        now = timezone.now()
        window_start = now - self.duration

        APIRequestLog.objects.filter(
            created_at__lt=window_start
        ).delete()

        request_count = APIRequestLog.objects.filter(
            user=request.user,
            created_at__gte=window_start,
        ).count()

        if request_count >= self.rate:
            self.wait_seconds = int(
                (
                    APIRequestLog.objects.filter(
                        user=request.user,
                        created_at__gte=window_start,
                    )
                    .order_by("created_at")
                    .first()
                    .created_at
                    + self.duration
                    - now
                ).total_seconds()
            )

            return False

        APIRequestLog.objects.create(
            user=request.user,
            path=request.path,
            method=request.method,
        )

        return True

    def wait(self):
        return getattr(self, "wait_seconds", 60)