import stripe
import requests

from django.conf import settings
from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from billing.services import create_invoice_from_payment
from subscriptions.services import activate_or_renew_subscription

from .models import Payment, WebhookEvent
from .serializers import PaymentSerializer, PaymentStatusSerializer, SSLCommerzCallbackSerializer, SSLCommerzCallbackResponseSerializer
from .services import create_payment_intent, get_payment_gateway


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by("-created_at")


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(user=request.user)

        try:
            if payment.gateway == "stripe":
                intent = create_payment_intent(payment)
                return Response({"payment": PaymentSerializer(payment).data, "client_secret": intent.client_secret}, status=status.HTTP_201_CREATED)

            gateway = get_payment_gateway(payment.gateway)
            result = gateway.create_payment(payment)

            response_data = {"payment": PaymentSerializer(payment).data, "detail": f"{payment.gateway} payment gateway is selected."}

            if payment.gateway == "sslcommerz" and result:
                response_data["gateway_url"] = result.get("GatewayPageURL")

            return Response(response_data, status=status.HTTP_201_CREATED)

        except stripe.error.StripeError as exc:
            payment.delete()
            return Response({"detail": "Unable to create Stripe PaymentIntent.", "error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        except NotImplementedError as exc:
            payment.delete()
            return Response({"detail": str(exc)}, status=status.HTTP_501_NOT_IMPLEMENTED)

        except RuntimeError as exc:
            payment.delete()
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception:
            payment.delete()
            return Response({"detail": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentStatusUpdateView(generics.UpdateAPIView):
    serializer_class = PaymentStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


class PaymentWebhookView(APIView):
    serializer_class = PaymentSerializer
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        if not sig_header:
            return Response({"detail": "Stripe signature header is missing."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except ValueError:
            return Response({"detail": "Invalid webhook payload."}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({"detail": "Invalid Stripe webhook signature."}, status=status.HTTP_400_BAD_REQUEST)

        event_id = event["id"]
        event_type = event["type"]
        existing_event = WebhookEvent.objects.filter(event_id=event_id).first()

        if existing_event:
            return Response({"detail": "Webhook event already processed."}, status=status.HTTP_200_OK)

        if event_type == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            payment = Payment.objects.filter(stripe_payment_intent_id=payment_intent["id"]).first()

            if not payment:
                return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

            payment.status = "successful"
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "paid_at", "updated_at"])

            if payment.subscription:
                activate_or_renew_subscription(payment.subscription)

            create_invoice_from_payment(payment)

        elif event_type == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]
            payment = Payment.objects.filter(stripe_payment_intent_id=payment_intent["id"]).first()

            if not payment:
                return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])

            if payment.subscription:
                payment.subscription.status = "past_due"
                payment.subscription.save(update_fields=["status", "updated_at"])

        else:
            return Response({"detail": "Event received but not handled.", "event_type": event_type}, status=status.HTTP_200_OK)

        WebhookEvent.objects.create(event_id=event_id, event_type=event_type, processed=True)
        return Response({"detail": "Stripe webhook processed successfully."}, status=status.HTTP_200_OK)


class SSLCommerzCallbackMixin:
    authentication_classes = []
    permission_classes = []

    def get_payment(self, transaction_id):
        return Payment.objects.filter(gateway="sslcommerz", transaction_id=transaction_id).first()

    def verify_payment(self, transaction_id):
        store_id = getattr(settings, "SSLCOMMERZ_STORE_ID", None)
        store_password = getattr(settings, "SSLCOMMERZ_STORE_PASSWORD", None)
        is_sandbox = getattr(settings, "SSLCOMMERZ_IS_SANDBOX", True)

        if not store_id or not store_password:
            return None, "SSLCommerz credentials are not configured."

        validation_url = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php" if is_sandbox else "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"

        try:
            response = requests.get(validation_url, params={"val_id": transaction_id, "store_id": store_id, "store_passwd": store_password, "format": "json"}, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return None, "Unable to verify SSLCommerz transaction."

        if data.get("status") not in {"VALID", "VALIDATED"}:
            return None, "SSLCommerz transaction validation failed."

        return data, None

    def complete_payment(self, payment, validation_data):
        if payment.status == "successful":
            return

        validated_amount = validation_data.get("amount")
        validated_currency = validation_data.get("currency")

        if validated_amount is None:
            raise ValueError("SSLCommerz validation response has no amount.")

        if str(validated_amount) != str(payment.amount):
            raise ValueError("SSLCommerz payment amount mismatch.")

        if validated_currency and validated_currency.lower() != payment.currency.lower():
            raise ValueError("SSLCommerz payment currency mismatch.")

        payment.status = "successful"
        payment.paid_at = timezone.now()
        payment.save(update_fields=["status", "paid_at", "updated_at"])

        if payment.subscription:
            activate_or_renew_subscription(payment.subscription)

        create_invoice_from_payment(payment)


@extend_schema(request=SSLCommerzCallbackSerializer, responses=SSLCommerzCallbackResponseSerializer)
class SSLCommerzSuccessView(SSLCommerzCallbackMixin, APIView):
    def post(self, request):
        transaction_id = request.data.get("tran_id")

        if not transaction_id:
            return Response({"detail": "SSLCommerz transaction ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        payment = self.get_payment(transaction_id)

        if not payment:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        validation_data, error = self.verify_payment(transaction_id)

        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.complete_payment(payment, validation_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "SSLCommerz payment completed successfully.", "payment_id": payment.id, "transaction_id": payment.transaction_id, "status": payment.status}, status=status.HTTP_200_OK)

    def get(self, request):
        return self.post(request)


@extend_schema(request=SSLCommerzCallbackSerializer, responses=SSLCommerzCallbackResponseSerializer)
class SSLCommerzFailView(SSLCommerzCallbackMixin, APIView):
    def post(self, request):
        transaction_id = request.data.get("tran_id")

        if not transaction_id:
            return Response({"detail": "SSLCommerz transaction ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        payment = self.get_payment(transaction_id)

        if not payment:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        payment.status = "failed"
        payment.save(update_fields=["status", "updated_at"])

        return Response({"detail": "SSLCommerz payment failed.", "payment_id": payment.id, "transaction_id": payment.transaction_id, "status": payment.status}, status=status.HTTP_200_OK)

    def get(self, request):
        return self.post(request)


@extend_schema(request=SSLCommerzCallbackSerializer, responses=SSLCommerzCallbackResponseSerializer)
class SSLCommerzCancelView(SSLCommerzCallbackMixin, APIView):
    def post(self, request):
        transaction_id = request.data.get("tran_id")

        if not transaction_id:
            return Response({"detail": "SSLCommerz transaction ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        payment = self.get_payment(transaction_id)

        if not payment:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        payment.status = "failed"
        payment.save(update_fields=["status", "updated_at"])

        return Response({"detail": "SSLCommerz payment was cancelled.", "payment_id": payment.id, "transaction_id": payment.transaction_id, "status": payment.status}, status=status.HTTP_200_OK)

    def get(self, request):
        return self.post(request)


@extend_schema(request=SSLCommerzCallbackSerializer, responses=SSLCommerzCallbackResponseSerializer)
class SSLCommerzIPNView(SSLCommerzCallbackMixin, APIView):
    def post(self, request):
        transaction_id = request.data.get("tran_id")

        if not transaction_id:
            return Response({"detail": "SSLCommerz transaction ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        payment = self.get_payment(transaction_id)

        if not payment:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        validation_data, error = self.verify_payment(transaction_id)

        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.complete_payment(payment, validation_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "SSLCommerz IPN processed successfully.", "payment_id": payment.id, "transaction_id": payment.transaction_id, "status": payment.status}, status=status.HTTP_200_OK)

    def get(self, request):
        return self.post(request)