from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from account.models import CustomUser
from .models import Plan, Subscription


class SubscriptionTests(TestCase):

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

        self.admin = CustomUser.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPassword123",
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

        self.pro_plan = Plan.objects.create(
            name="Pro",
            price="25.00",
            billing_cycle="monthly",
            max_projects=10,
            max_api_requests=1000,
            storage_limit_gb="10.00",
            is_active=True,
        )

    # Plan List

    def test_plan_list(self):
        response = self.client.get(
            reverse("plan-list-create")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 2)

    # Plan Create

    def test_admin_can_create_plan(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("plan-list-create"),
            {
                "name": "Enterprise",
                "price": "50.00",
                "billing_cycle": "yearly",
                "max_projects": 50,
                "max_api_requests": 5000,
                "storage_limit_gb": "50.00",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Plan.objects.filter(name="Enterprise").exists()
        )

    def test_normal_user_cannot_create_plan(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("plan-list-create"),
            {
                "name": "Enterprise",
                "price": "50.00",
                "billing_cycle": "yearly",
                "max_projects": 50,
                "max_api_requests": 5000,
                "storage_limit_gb": "50.00",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    # Plan Detail

    def test_admin_can_view_plan_detail(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                "plan-detail",
                kwargs={"pk": self.plan.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["name"],
            "Basic",
        )

    def test_admin_can_update_plan(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            reverse(
                "plan-detail",
                kwargs={"pk": self.plan.id},
            ),
            {
                "price": "15.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.plan.refresh_from_db()

        self.assertEqual(
            str(self.plan.price),
            "15.00",
        )

    def test_normal_user_cannot_update_plan(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                "plan-detail",
                kwargs={"pk": self.plan.id},
            ),
            {
                "price": "15.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_can_delete_plan(self):
        self.client.force_authenticate(user=self.admin)

        plan = Plan.objects.create(
            name="Delete Plan",
            price="5.00",
            billing_cycle="monthly",
            max_projects=1,
            max_api_requests=10,
            storage_limit_gb="1.00",
            is_active=True,
        )

        response = self.client.delete(
            reverse(
                "plan-detail",
                kwargs={"pk": plan.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Plan.objects.filter(id=plan.id).exists()
        )

    # Subscription List

    def test_authenticated_user_can_view_subscriptions(self):
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("subscription-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)

    def test_unauthenticated_user_cannot_view_subscriptions(self):
        response = self.client.get(
            reverse("subscription-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_only_sees_own_subscriptions(self):
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
        )

        Subscription.objects.create(
            user=self.other_user,
            plan=self.pro_plan,
            status="active",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("subscription-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)

        self.assertEqual(
            response.data[0]["plan"]["name"],
            "Basic",
        )

    # Subscription Detail

    def test_user_can_view_own_subscription(self):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                "subscription-detail",
                kwargs={"pk": subscription.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["plan"]["name"],
            "Basic",
        )

    def test_user_cannot_view_other_users_subscription(self):
        subscription = Subscription.objects.create(
            user=self.other_user,
            plan=self.pro_plan,
            status="active",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                "subscription-detail",
                kwargs={"pk": subscription.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # Subscribe

    def test_user_can_subscribe(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("subscribe"),
            {
                "plan_id": self.plan.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Subscription.objects.filter(
                user=self.user,
                plan=self.plan,
                status="active",
            ).exists()
        )

    def test_unauthenticated_user_cannot_subscribe(self):
        response = self.client.post(
            reverse("subscribe"),
            {
                "plan_id": self.plan.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_cannot_subscribe_to_invalid_plan(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("subscribe"),
            {
                "plan_id": 99999,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_cannot_subscribe_to_inactive_plan(self):
        inactive_plan = Plan.objects.create(
            name="Inactive",
            price="20.00",
            billing_cycle="monthly",
            max_projects=5,
            max_api_requests=500,
            storage_limit_gb="5.00",
            is_active=False,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("subscribe"),
            {
                "plan_id": inactive_plan.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_cannot_have_two_active_subscriptions(self):
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("subscribe"),
            {
                "plan_id": self.pro_plan.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            Subscription.objects.filter(
                user=self.user,
                status="active",
            ).count(),
            1,
        )