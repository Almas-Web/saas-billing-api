from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from account.models import CustomUser
from subscriptions.models import Plan, Subscription
from projects.models import Project

from .models import UsageRecord
from .serializers import UsageRecordSerializer
from .services import (
    get_current_usage,
    increment_api_requests,
    update_projects_count,
    update_storage_usage,
    check_api_request_limit,
    check_project_limit,
    increment_projects_count,
    decrement_projects_count,
    check_storage_limit,
    add_storage_usage,
)


class UsageTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            is_verified=True,
        )

        self.other_user = CustomUser.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="TestPassword123",
            is_verified=True,
        )

        self.plan = Plan.objects.create(
            name="Basic",
            price="10.00",
            billing_cycle="monthly",
            max_projects=3,
            max_api_requests=100,
            storage_limit_gb="1.00",
            is_active=True,
        )

        self.subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
        )

        self.usage = UsageRecord.objects.create(
            user=self.user,
            plan=self.plan,
            api_requests=25,
            projects_count=0,
            storage_used_gb=Decimal("0.25"),
            period_start=timezone.now() - timedelta(days=10),
            period_end=timezone.now() + timedelta(days=20),
        )

    def test_authenticated_user_can_view_current_usage(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["user"],
            self.user.id,
        )

    def test_unauthenticated_user_cannot_view_current_usage(self):
        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_current_usage_creates_record_when_missing(self):
        UsageRecord.objects.filter(
            user=self.user
        ).delete()

        usage = get_current_usage(
            self.user
        )

        self.assertIsNotNone(
            usage
        )

        self.assertEqual(
            usage.user,
            self.user,
        )

        self.assertEqual(
            usage.plan,
            self.plan,
        )

        self.assertEqual(
            usage.api_requests,
            0,
        )

        self.assertEqual(
            usage.projects_count,
            0,
        )

    def test_current_plan_is_returned(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.data["current_plan"],
            "Basic",
        )

    def test_api_usage_limit(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.data["api_requests"],
            26,
        )

        self.assertEqual(
            response.data["api_requests_limit"],
            100,
        )

    def test_api_requests_remaining(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.data["api_requests_remaining"],
            74,
        )

    def test_api_requests_percentage(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            Decimal(
                str(
                    response.data[
                        "api_requests_percentage"
                    ]
                )
            ),
            Decimal("26.00"),
        )

    def test_api_limit_status_available(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.data["api_limit_status"],
            "AVAILABLE",
        )

    def test_api_limit_service(self):
        self.usage.api_requests = 99
        self.usage.save()

        self.assertTrue(
            check_api_request_limit(
                self.user
            )
        )

    def test_api_limit_service_reached(self):
        self.usage.api_requests = 100
        self.usage.save()

        from rest_framework.exceptions import PermissionDenied

        with self.assertRaises(
            PermissionDenied
        ):
            check_api_request_limit(
                self.user
            )

    def test_increment_api_requests(self):
        usage = increment_api_requests(
            self.user,
            amount=5,
        )

        self.assertEqual(
            usage.api_requests,
            30,
        )

    def test_projects_limit_uses_actual_project_count(self):
        Project.objects.create(
            user=self.user,
            name="Project One",
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.data["projects_count"],
            1,
        )

        self.assertEqual(
            response.data["projects_limit"],
            3,
        )

    def test_projects_remaining(self):
        Project.objects.create(
            user=self.user,
            name="Project One",
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.data["projects_remaining"],
            2,
        )

    def test_projects_percentage(self):
        Project.objects.create(
            user=self.user,
            name="Project One",
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            Decimal(
                str(
                    response.data[
                        "projects_percentage"
                    ]
                )
            ),
            Decimal("33.33"),
        )

    def test_project_limit_status_available(self):
        Project.objects.create(
            user=self.user,
            name="Project One",
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.data[
                "project_limit_status"
            ],
            "AVAILABLE",
        )

    def test_project_limit_service(self):
        Project.objects.create(
            user=self.user,
            name="Project One",
        )

        self.assertTrue(
            check_project_limit(
                self.user
            )
        )

    def test_project_limit_service_reached(self):
        for number in range(3):
            Project.objects.create(
                user=self.user,
                name=f"Project {number}",
            )

        from rest_framework.exceptions import PermissionDenied

        with self.assertRaises(
            PermissionDenied
        ):
            check_project_limit(
                self.user
            )

    def test_update_projects_count(self):
        usage = update_projects_count(
            self.user,
            2,
        )

        self.assertEqual(
            usage.projects_count,
            2,
        )

    def test_increment_projects_count(self):
        usage = increment_projects_count(
            self.user,
            amount=2,
        )

        self.assertEqual(
            usage.projects_count,
            2,
        )

    def test_decrement_projects_count(self):
        Project.objects.create(
            user=self.user,
            name="Project One",
        )

        get_current_usage(
            self.user
        )

        usage = decrement_projects_count(
            self.user,
            amount=1,
        )

        self.assertEqual(
            usage.projects_count,
            0,
        )

    def test_decrement_projects_count_does_not_go_negative(self):
        usage = decrement_projects_count(
            self.user,
            amount=5,
        )

        self.assertEqual(
            usage.projects_count,
            0,
        )

    def test_storage_limit(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            Decimal(
                str(
                    response.data[
                        "storage_limit_gb"
                    ]
                )
            ),
            Decimal("1.00"),
        )

    def test_storage_remaining(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            Decimal(
                str(
                    response.data[
                        "storage_remaining_gb"
                    ]
                )
            ),
            Decimal("0.75"),
        )

    def test_storage_percentage(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            Decimal(
                str(
                    response.data[
                        "storage_percentage"
                    ]
                )
            ),
            Decimal("25.00"),
        )

    def test_storage_limit_status_available(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertEqual(
            response.data[
                "storage_limit_status"
            ],
            "AVAILABLE",
        )

    def test_storage_limit_service(self):
        self.assertTrue(
            check_storage_limit(
                self.user,
                Decimal("0.50"),
            )
        )

    def test_storage_limit_service_reached(self):
        from rest_framework.exceptions import PermissionDenied

        with self.assertRaises(
            PermissionDenied
        ):
            check_storage_limit(
                self.user,
                Decimal("0.80"),
            )

    def test_update_storage_usage(self):
        usage = update_storage_usage(
            self.user,
            Decimal("0.50"),
        )

        self.assertEqual(
            usage.storage_used_gb,
            Decimal("0.50"),
        )

    def test_add_storage_usage(self):
        usage = add_storage_usage(
            self.user,
            Decimal("0.25"),
        )

        self.assertEqual(
            usage.storage_used_gb,
            Decimal("0.50"),
        )

    def test_usage_percentage_does_not_exceed_100(self):
        self.usage.api_requests = 150
        self.usage.projects_count = 5
        self.usage.storage_used_gb = Decimal(
            "2.00"
        )
        self.usage.save()

        self.usage.refresh_from_db()

        serializer = UsageRecordSerializer(
            self.usage
        )

        data = serializer.data

        self.assertEqual(
            Decimal(
                str(
                    data[
                        "api_requests_percentage"
                    ]
                )
            ),
            Decimal("100.00"),
        )

        self.assertEqual(
            Decimal(
                str(
                    data[
                        "projects_percentage"
                    ]
                )
            ),
            Decimal("100.00"),
        )

        self.assertEqual(
            Decimal(
                str(
                    data[
                        "storage_percentage"
                    ]
                )
            ),
            Decimal("100.00"),
        )

    def test_remaining_usage_does_not_become_negative(self):
        self.usage.api_requests = 150
        self.usage.projects_count = 5
        self.usage.storage_used_gb = Decimal(
            "2.00"
        )
        self.usage.save()

        self.usage.refresh_from_db()

        serializer = UsageRecordSerializer(
            self.usage
        )

        data = serializer.data

        self.assertEqual(
            data["api_requests_remaining"],
            0,
        )

        self.assertEqual(
            data["projects_remaining"],
            0,
        )

        self.assertEqual(
            Decimal(
                str(
                    data[
                        "storage_remaining_gb"
                    ]
                )
            ),
            Decimal("0.00"),
        )

    def test_usage_period_is_returned(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("current-usage")
        )

        self.assertIsNotNone(
            response.data["period_start"]
        )

        self.assertIsNotNone(
            response.data["period_end"]
        )

    def test_usage_belongs_to_correct_user(self):
        self.assertEqual(
            self.usage.user,
            self.user,
        )

    def test_usage_is_connected_to_plan(self):
        self.assertEqual(
            self.usage.plan,
            self.plan,
        )

    def test_usage_can_have_no_plan(self):
        usage = UsageRecord.objects.create(
            user=self.other_user,
            plan=None,
            api_requests=10,
            projects_count=0,
            storage_used_gb=Decimal(
                "0.10"
            ),
            period_start=timezone.now(),
            period_end=timezone.now()
            + timedelta(days=30),
        )

        serializer = UsageRecordSerializer(
            usage
        )

        data = serializer.data

        self.assertIsNone(
            data["current_plan"]
        )

        self.assertEqual(
            data["api_requests_limit"],
            0,
        )

        self.assertEqual(
            data["projects_limit"],
            0,
        )

        self.assertEqual(
            Decimal(
                str(
                    data[
                        "storage_limit_gb"
                    ]
                )
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            data["api_limit_status"],
            "NO_SUBSCRIPTION",
        )

        self.assertEqual(
            data["project_limit_status"],
            "NO_SUBSCRIPTION",
        )

        self.assertEqual(
            data["storage_limit_status"],
            "NO_SUBSCRIPTION",
        )