from decimal import Decimal

import stripe
from django.conf import settings


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment_intent(payment):
    amount = int(Decimal(payment.amount) * 100)

    metadata = {
        "payment_id": str(payment.id),
        "user_id": str(payment.user.id),
    }

    if payment.subscription:
        metadata["subscription_id"] = str(payment.subscription.id)

    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency=payment.currency.lower(),
        metadata=metadata,
    )

    payment.stripe_payment_intent_id = intent.id
    payment.save(
        update_fields=[
            "stripe_payment_intent_id",
            "updated_at",
        ]
    )

    return intent