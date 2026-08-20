from decimal import Decimal
from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from account.models import CustomUser
from subscriptions.models import Plan, Subscription
from .models import Payment, WebhookEvent

@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret")
class PaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(username="testuser", email="test@example.com", password="TestPassword123", is_verified=True)
        self.other_user = CustomUser.objects.create_user(username="otheruser", email="other@example.com", password="TestPassword123", is_verified=True)
        self.plan = Plan.objects.create(name="Basic", price="10.00", billing_cycle="monthly", max_projects=3, max_api_requests=100, storage_limit_gb="1.00", is_active=True)
        self.subscription = Subscription.objects.create(user=self.user, plan=self.plan, status="active")
        self.payment = Payment.objects.create(user=self.user, subscription=self.subscription, amount=Decimal("10.00"), currency="usd", status="pending", stripe_payment_intent_id="pi_test_123")

    def test_authenticated_user_can_view_payment_list(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("payment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["amount"], "10.00")

    def test_unauthenticated_user_cannot_view_payment_list(self):
        response = self.client.get(reverse("payment-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_only_sees_own_payments(self):
        Payment.objects.create(user=self.other_user, amount=Decimal("20.00"), currency="usd", status="pending")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("payment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["amount"], "10.00")

    def test_user_can_view_own_payment(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("payment-detail", kwargs={"pk": self.payment.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["stripe_payment_intent_id"], "pi_test_123")

    def test_user_cannot_view_other_users_payment(self):
        other_payment = Payment.objects.create(user=self.other_user, amount=Decimal("20.00"), currency="usd", status="pending")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("payment-detail", kwargs={"pk": other_payment.id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("payments.views.create_payment_intent")
    def test_user_can_create_payment(self, mock_create_payment_intent):
        mock_intent = Mock()
        mock_intent.client_secret = "pi_test_client_secret"
        mock_intent.id = "pi_test_new"
        mock_create_payment_intent.return_value = mock_intent
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("payment-create"), {"subscription": self.subscription.id, "amount": "10.00", "currency": "usd"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment", response.data)
        self.assertIn("client_secret", response.data)
        self.assertEqual(response.data["client_secret"], "pi_test_client_secret")
        self.assertTrue(Payment.objects.filter(user=self.user, amount=Decimal("10.00")).exists())
        mock_create_payment_intent.assert_called_once()

    def test_unauthenticated_user_cannot_create_payment(self):
        response = self.client.post(reverse("payment-create"), {"subscription": self.subscription.id, "amount": "10.00", "currency": "usd"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("payments.views.create_payment_intent")
    def test_stripe_error_during_payment_creation(self, mock_create_payment_intent):
        import stripe
        mock_create_payment_intent.side_effect = stripe.error.StripeError("Stripe error")
        before_count = Payment.objects.count()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("payment-create"), {"subscription": self.subscription.id, "amount": "10.00", "currency": "usd"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["detail"], "Unable to create Stripe PaymentIntent.")
        self.assertEqual(Payment.objects.count(), before_count)

    @patch("payments.views.create_payment_intent")
    def test_unexpected_error_during_payment_creation(self, mock_create_payment_intent):
        mock_create_payment_intent.side_effect = Exception("Unexpected error")
        before_count = Payment.objects.count()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("payment-create"), {"subscription": self.subscription.id, "amount": "10.00", "currency": "usd"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(Payment.objects.count(), before_count)

    def test_user_can_update_payment_status(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("payment-status-update", kwargs={"pk": self.payment.id}), {"status": "successful"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "successful")

    def test_user_cannot_update_other_users_payment_status(self):
        other_payment = Payment.objects.create(user=self.other_user, amount=Decimal("20.00"), currency="usd", status="pending")
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("payment-status-update", kwargs={"pk": other_payment.id}), {"status": "successful"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_user_cannot_update_payment_status(self):
        response = self.client.patch(reverse("payment-status-update", kwargs={"pk": self.payment.id}), {"status": "successful"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sslcommerz_returns_not_implemented(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("payment-create"), {"subscription": self.subscription.id, "gateway": "sslcommerz", "amount": "10.00", "currency": "bdt"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        self.assertIn("SSLCommerz integration is not configured yet.", response.data["detail"])
        self.assertEqual(Payment.objects.filter(user=self.user, gateway="sslcommerz").count(), 0)

    def test_bkash_returns_not_implemented(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("payment-create"), {"subscription": self.subscription.id, "gateway": "bkash", "amount": "10.00", "currency": "bdt"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        self.assertIn("bKash integration is not configured yet.", response.data["detail"])
        self.assertEqual(Payment.objects.filter(user=self.user, gateway="bkash").count(), 0)

    def test_nagad_returns_not_implemented(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("payment-create"), {"subscription": self.subscription.id, "gateway": "nagad", "amount": "10.00", "currency": "bdt"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        self.assertIn("Nagad integration is not configured yet.", response.data["detail"])
        self.assertEqual(Payment.objects.filter(user=self.user, gateway="nagad").count(), 0)

    def test_webhook_requires_signature(self):
        response = self.client.post(reverse("payment-webhook"), data=b'{"id": "evt_test_123"}', content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Stripe signature header is missing.")

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_webhook_invalid_payload(self, mock_construct_event):
        mock_construct_event.side_effect = ValueError()
        response = self.client.post(reverse("payment-webhook"), data=b"invalid-payload", content_type="application/json", HTTP_STRIPE_SIGNATURE="invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid webhook payload.")

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_webhook_invalid_signature(self, mock_construct_event):
        import stripe
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError("Invalid signature", "sig_header")
        response = self.client.post(reverse("payment-webhook"), data=b"test-payload", content_type="application/json", HTTP_STRIPE_SIGNATURE="invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid Stripe webhook signature.")

    @patch("payments.views.create_invoice_from_payment")
    @patch("payments.views.stripe.Webhook.construct_event")
    def test_successful_payment_webhook(self, mock_construct_event, mock_create_invoice):
        mock_construct_event.return_value = {"id": "evt_success_123", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_test_123"}}}
        response = self.client.post(reverse("payment-webhook"), data=b"test-payload", content_type="application/json", HTTP_STRIPE_SIGNATURE="valid-signature")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(self.payment.status, "successful")
        self.assertIsNotNone(self.payment.paid_at)
        self.assertEqual(self.subscription.status, "active")
        self.assertTrue(WebhookEvent.objects.filter(event_id="evt_success_123", event_type="payment_intent.succeeded", processed=True).exists())
        mock_create_invoice.assert_called_once_with(self.payment)

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_failed_payment_webhook(self, mock_construct_event):
        mock_construct_event.return_value = {"id": "evt_failed_123", "type": "payment_intent.payment_failed", "data": {"object": {"id": "pi_test_123"}}}
        response = self.client.post(reverse("payment-webhook"), data=b"test-payload", content_type="application/json", HTTP_STRIPE_SIGNATURE="valid-signature")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(self.payment.status, "failed")
        self.assertEqual(self.subscription.status, "past_due")
        self.assertTrue(WebhookEvent.objects.filter(event_id="evt_failed_123", event_type="payment_intent.payment_failed", processed=True).exists())

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_webhook_payment_not_found(self, mock_construct_event):
        mock_construct_event.return_value = {"id": "evt_not_found_123", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_not_found"}}}
        response = self.client.post(reverse("payment-webhook"), data=b"test-payload", content_type="application/json", HTTP_STRIPE_SIGNATURE="valid-signature")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_duplicate_webhook_is_not_processed(self, mock_construct_event):
        WebhookEvent.objects.create(event_id="evt_duplicate_123", event_type="payment_intent.succeeded", processed=True)
        mock_construct_event.return_value = {"id": "evt_duplicate_123", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_test_123"}}}
        response = self.client.post(reverse("payment-webhook"), data=b"test-payload", content_type="application/json", HTTP_STRIPE_SIGNATURE="valid-signature")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_unhandled_webhook_event(self, mock_construct_event):
        mock_construct_event.return_value = {"id": "evt_unhandled_123", "type": "customer.created", "data": {"object": {}}}
        response = self.client.post(reverse("payment-webhook"), data=b"test-payload", content_type="application/json", HTTP_STRIPE_SIGNATURE="valid-signature")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["event_type"], "customer.created")
        self.assertFalse(WebhookEvent.objects.filter(event_id="evt_unhandled_123").exists())