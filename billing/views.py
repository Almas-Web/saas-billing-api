from rest_framework import generics, permissions
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from .services import generate_invoice_pdf
from .models import Invoice
from .serializers import InvoiceSerializer

@extend_schema(tags=["Billing"])
class InvoiceListView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user).order_by("-created_at")

@extend_schema(tags=["Billing"])
class InvoiceDetailView(generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

@extend_schema(tags=["Billing"])
class InvoicePDFDownloadView(generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()
        pdf_buffer = generate_invoice_pdf(invoice)
        filename = f"invoice-{invoice.id}.pdf"
        response = FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/pdf"
        )
        return response