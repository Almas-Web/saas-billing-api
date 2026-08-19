from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from account.models import CustomUser
from subscriptions.models import Plan, Subscription
from payments.models import Payment

from .models import Invoice


class InvoiceTests(TestCase):

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

        self.payment = Payment.objects.create(
            user=self.user,
            subscription=self.subscription,
            amount=Decimal("10.00"),
            currency="usd",
            status="successful",
            stripe_payment_intent_id="pi_invoice_test",
        )

        self.invoice = Invoice.objects.create(
            user=self.user,
            subscription=self.subscription,
            payment=self.payment,
            amount=Decimal("10.00"),
            currency="usd",
            status="paid",
        )

    def test_authenticated_user_can_view_invoice_list(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("invoice-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["amount"],
            "10.00",
        )

        self.assertEqual(
            response.data[0]["status"],
            "paid",
        )

    def test_unauthenticated_user_cannot_view_invoice_list(self):
        response = self.client.get(
            reverse("invoice-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_only_sees_own_invoices(self):
        Invoice.objects.create(
            user=self.other_user,
            amount=Decimal("20.00"),
            currency="usd",
            status="open",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("invoice-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["amount"],
            "10.00",
        )

    def test_user_can_view_own_invoice(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                "invoice-detail",
                kwargs={"pk": self.invoice.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.invoice.id,
        )

        self.assertEqual(
            response.data["amount"],
            "10.00",
        )

    def test_user_cannot_view_other_users_invoice(self):
        other_invoice = Invoice.objects.create(
            user=self.other_user,
            amount=Decimal("20.00"),
            currency="usd",
            status="open",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                "invoice-detail",
                kwargs={"pk": other_invoice.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_user_cannot_view_invoice_detail(self):
        response = self.client.get(
            reverse(
                "invoice-detail",
                kwargs={"pk": self.invoice.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_invoice_is_created_with_correct_user(self):
        self.assertEqual(
            self.invoice.user,
            self.user,
        )

    def test_invoice_is_connected_to_subscription(self):
        self.assertEqual(
            self.invoice.subscription,
            self.subscription,
        )

    def test_invoice_is_connected_to_payment(self):
        self.assertEqual(
            self.invoice.payment,
            self.payment,
        )

    def test_invoice_amount_and_currency(self):
        self.assertEqual(
            self.invoice.amount,
            Decimal("10.00"),
        )

        self.assertEqual(
            self.invoice.currency,
            "usd",
        )

    def test_paid_invoice_status(self):
        self.assertEqual(
            self.invoice.status,
            "paid",
        )

    def test_invoice_can_have_draft_status(self):
        invoice = Invoice.objects.create(
            user=self.user,
            amount=Decimal("15.00"),
            currency="usd",
            status="draft",
        )

        self.assertEqual(
            invoice.status,
            "draft",
        )

    def test_invoice_can_have_open_status(self):
        invoice = Invoice.objects.create(
            user=self.user,
            amount=Decimal("15.00"),
            currency="usd",
            status="open",
        )

        self.assertEqual(
            invoice.status,
            "open",
        )

    def test_invoice_can_have_void_status(self):
        invoice = Invoice.objects.create(
            user=self.user,
            amount=Decimal("15.00"),
            currency="usd",
            status="void",
        )

        self.assertEqual(
            invoice.status,
            "void",
        )

    def test_invoice_can_have_uncollectible_status(self):
        invoice = Invoice.objects.create(
            user=self.user,
            amount=Decimal("15.00"),
            currency="usd",
            status="uncollectible",
        )

        self.assertEqual(
            invoice.status,
            "uncollectible",
        )

    def test_payment_can_have_one_invoice(self):
        self.assertEqual(
            self.payment.invoice,
            self.invoice,
        )

    def test_invoice_payment_can_be_null(self):
        invoice = Invoice.objects.create(
            user=self.user,
            subscription=self.subscription,
            amount=Decimal("25.00"),
            currency="usd",
            status="draft",
        )

        self.assertIsNone(
            invoice.payment,
        )

    def test_invoice_subscription_can_be_null(self):
        invoice = Invoice.objects.create(
            user=self.user,
            payment=None,
            amount=Decimal("25.00"),
            currency="usd",
            status="draft",
        )

        self.assertIsNone(
            invoice.subscription,
        )

    def test_invoice_list_is_ordered_by_created_at(self):
        first_invoice = self.invoice

        second_invoice = Invoice.objects.create(
            user=self.user,
            amount=Decimal("20.00"),
            currency="usd",
            status="open",
        )

        Invoice.objects.filter(
            id=first_invoice.id
        ).update(
            created_at=timezone.now() - timedelta(minutes=10)
        )

        Invoice.objects.filter(
            id=second_invoice.id
        ).update(
            created_at=timezone.now()
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("invoice-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data[0]["id"],
            second_invoice.id,
        )

        self.assertEqual(
            response.data[1]["id"],
            first_invoice.id,
        )