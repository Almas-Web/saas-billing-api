from django.utils import timezone

from .models import Invoice
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


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



def generate_invoice_pdf(invoice):
    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    pdf.setTitle(f"Invoice #{invoice.id}")

    # Header
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, height - 60, "INVOICE")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50,
        height - 85,
        f"Invoice #: {invoice.id}",
    )

    pdf.drawString(
        50,
        height - 105,
        f"Invoice Date: {invoice.invoice_date.strftime('%Y-%m-%d')}",
    )

    # User information
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 145, "Customer")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50,
        height - 165,
        f"Username: {invoice.user.username}",
    )

    pdf.drawString(
        50,
        height - 185,
        f"Email: {invoice.user.email}",
    )

    # Subscription
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 225, "Subscription")

    pdf.setFont("Helvetica", 11)

    plan_name = (
        invoice.subscription.plan.name
        if invoice.subscription
        else "N/A"
    )

    pdf.drawString(
        50,
        height - 245,
        f"Plan: {plan_name}",
    )

    if invoice.subscription:
        pdf.drawString(
            50,
            height - 265,
            f"Billing Cycle: {invoice.subscription.plan.billing_cycle}",
        )

    # Payment information
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 305, "Payment")

    pdf.setFont("Helvetica", 11)

    pdf.drawString(
        50,
        height - 325,
        f"Amount: {invoice.amount} {invoice.currency.upper()}",
    )

    pdf.drawString(
        50,
        height - 345,
        f"Status: {invoice.status.title()}",
    )

    if invoice.paid_at:
        pdf.drawString(
            50,
            height - 365,
            f"Paid At: {invoice.paid_at.strftime('%Y-%m-%d %H:%M:%S')}",
        )

    # Footer
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        50,
        50,
        "Thank you for your business.",
    )

    pdf.save()

    buffer.seek(0)

    return buffer