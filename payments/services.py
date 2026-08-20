from decimal import Decimal
import stripe
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
    def create_payment(self, payment):
        raise NotImplementedError("SSLCommerz integration is not configured yet.")

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