from decimal import Decimal
import requests
import stripe
import uuid
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentGateway:
    def create_payment(self, payment):
        raise NotImplementedError("Payment gateway must implement create_payment().")


class StripeGateway(PaymentGateway):
    def create_payment(self, payment):
        amount = int(Decimal(payment.amount) * 100)
        metadata = {"payment_id": str(payment.id), "user_id": str(payment.user.id)}
        if payment.subscription:
            metadata["subscription_id"] = str(payment.subscription.id)
        intent = stripe.PaymentIntent.create(amount=amount, currency=payment.currency.lower(), metadata=metadata)
        payment.stripe_payment_intent_id = intent.id
        payment.transaction_id = intent.id
        payment.save(update_fields=["stripe_payment_intent_id", "transaction_id", "updated_at"])
        return intent


class SSLCommerzGateway(PaymentGateway):
    SANDBOX_URL = "https://sandbox-gw.sslcommerz.com/gwprocess/v4/api.php"
    LIVE_URL = "https://securepay.sslcommerz.com/gwprocess/v4/api.php"

    def create_payment(self, payment):
        store_id = getattr(settings, "SSLCOMMERZ_STORE_ID", None)
        store_password = getattr(settings, "SSLCOMMERZ_STORE_PASSWORD", None)
        is_sandbox = getattr(settings, "SSLCOMMERZ_IS_SANDBOX", True)

        if not store_id or not store_password:
            raise RuntimeError("SSLCommerz credentials are not configured.")

        if not payment.transaction_id:
            payment.transaction_id = f"SSL-{payment.id}-{uuid.uuid4().hex[:12].upper()}"
            payment.save(update_fields=["transaction_id", "updated_at"])

        base_url = self.SANDBOX_URL if is_sandbox else self.LIVE_URL

        payload = {
            "store_id": store_id,
            "store_passwd": store_password,
            "total_amount": str(payment.amount),
            "currency": payment.currency.upper(),
            "tran_id": payment.transaction_id,
            "success_url": settings.SSLCOMMERZ_SUCCESS_URL,
            "fail_url": settings.SSLCOMMERZ_FAIL_URL,
            "cancel_url": settings.SSLCOMMERZ_CANCEL_URL,
            "ipn_url": settings.SSLCOMMERZ_IPN_URL,
            "cus_name": payment.user.get_full_name() or payment.user.email,
            "cus_email": payment.user.email,
            "cus_add1": "N/A",
            "cus_city": "Dhaka",
            "cus_postcode": "1000",
            "cus_country": "Bangladesh",
            "cus_phone": getattr(payment.user, "phone", None) or "01700000000",
            "shipping_method": "NO",
            "num_of_item": 1,
            "product_name": payment.subscription.plan.name if payment.subscription else "SaaS Subscription",
            "product_category": "subscription",
            "product_profile": "non-physical-goods",
        }

        response = requests.post(base_url, data=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "SUCCESS":
            raise RuntimeError(
                data.get("failedreason")
                or data.get("error_reason")
                or "SSLCommerz payment initiation failed."
            )

        gateway_url = data.get("GatewayPageURL")

        if not gateway_url:
            raise RuntimeError("SSLCommerz did not return GatewayPageURL.")

        return data


class BkashGateway(PaymentGateway):
    def create_payment(self, payment):
        raise NotImplementedError("bKash integration is not configured yet.")


class NagadGateway(PaymentGateway):
    def create_payment(self, payment):
        raise NotImplementedError("Nagad integration is not configured yet.")


def get_payment_gateway(gateway):
    gateways = {
        "stripe": StripeGateway(),
        "sslcommerz": SSLCommerzGateway(),
        "bkash": BkashGateway(),
        "nagad": NagadGateway(),
    }

    gateway_instance = gateways.get(gateway)

    if gateway_instance is None:
        raise ValueError(f"Unsupported payment gateway: {gateway}")

    return gateway_instance


def create_payment(payment):
    gateway = get_payment_gateway(payment.gateway)
    return gateway.create_payment(payment)


def create_payment_intent(payment):
    return StripeGateway().create_payment(payment)