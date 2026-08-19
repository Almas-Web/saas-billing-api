from django.utils import timezone

from .models import Invoice


def create_invoice_from_payment(payment):
    invoice, created = Invoice.objects.get_or_create(
        payment=payment,
        defaults={
            "user": payment.user,
            "subscription": payment.subscription,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": "paid",
            "paid_at": timezone.now(),
        },
    )

    return invoice


def create_invoice_from_subscription(subscription):
    payment = subscription.payments.filter(
        status="successful"
    ).order_by("-created_at").first()

    if not payment:
        return None

    return create_invoice_from_payment(payment)


def sync_invoice_status_from_payment(payment):
    invoice = Invoice.objects.filter(
        payment=payment
    ).first()

    if not invoice:
        return None

    status_mapping = {
        "pending": "open",
        "successful": "paid",
        "failed": "uncollectible",
        "refunded": "void",
    }

    new_status = status_mapping.get(payment.status)

    if not new_status:
        return invoice

    invoice.status = new_status

    if payment.status == "successful" and not invoice.paid_at:
        invoice.paid_at = timezone.now()

    if payment.status != "successful":
        invoice.paid_at = None

    invoice.save(
        update_fields=[
            "status",
            "paid_at",
            "updated_at",
        ]
    )

    return invoice