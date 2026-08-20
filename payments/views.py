import stripe

from django.conf import settings
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from billing.services import create_invoice_from_payment
from .models import Payment, WebhookEvent
from .serializers import PaymentSerializer, PaymentStatusSerializer
from .services import create_payment_intent, get_payment_gateway
from subscriptions.services import activate_or_renew_subscription


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

                return Response(
                    {
                        "payment": PaymentSerializer(payment).data,
                        "client_secret": intent.client_secret,
                    },
                    status=status.HTTP_201_CREATED,
                )

            gateway = get_payment_gateway(payment.gateway)
            gateway.create_payment(payment)

            return Response(
                {
                    "payment": PaymentSerializer(payment).data,
                    "detail": f"{payment.gateway} payment gateway is selected.",
                },
                status=status.HTTP_201_CREATED,
            )

        except stripe.error.StripeError as exc:
            payment.delete()

            return Response(
                {
                    "detail": "Unable to create Stripe PaymentIntent.",
                    "error": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except NotImplementedError as exc:
            payment.delete()

            return Response(
                {"detail": str(exc)},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        except Exception:
            payment.delete()

            return Response(
                {"detail": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PaymentStatusUpdateView(generics.UpdateAPIView):
    serializer_class = PaymentStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


class PaymentWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        if not sig_header:
            return Response(
                {"detail": "Stripe signature header is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET,
            )

        except ValueError:
            return Response(
                {"detail": "Invalid webhook payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except stripe.error.SignatureVerificationError:
            return Response(
                {"detail": "Invalid Stripe webhook signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_id = event["id"]
        event_type = event["type"]

        existing_event = WebhookEvent.objects.filter(event_id=event_id).first()

        if existing_event:
            return Response(
                {"detail": "Webhook event already processed."},
                status=status.HTTP_200_OK,
            )

        if event_type == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]

            payment = Payment.objects.filter(
                stripe_payment_intent_id=payment_intent["id"]
            ).first()

            if not payment:
                return Response(
                    {"detail": "Payment not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            payment.status = "successful"
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "paid_at", "updated_at"])

            if payment.subscription:
                activate_or_renew_subscription(payment.subscription)

            create_invoice_from_payment(payment)

        elif event_type == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]

            payment = Payment.objects.filter(
                stripe_payment_intent_id=payment_intent["id"]
            ).first()

            if not payment:
                return Response(
                    {"detail": "Payment not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])

            if payment.subscription:
                payment.subscription.status = "past_due"
                payment.subscription.save(
                    update_fields=["status", "updated_at"]
                )

        else:
            return Response(
                {
                    "detail": "Event received but not handled.",
                    "event_type": event_type,
                },
                status=status.HTTP_200_OK,
            )

        WebhookEvent.objects.create(
            event_id=event_id,
            event_type=event_type,
            processed=True,
        )

        return Response(
            {"detail": "Stripe webhook processed successfully."},
            status=status.HTTP_200_OK,
        )