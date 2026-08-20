from django.urls import path
from .views import InvoiceListView, InvoiceDetailView, InvoicePDFDownloadView


urlpatterns = [
    path(
        "invoices/",
        InvoiceListView.as_view(),
        name="invoice-list",
    ),
    path(
        "invoices/<int:pk>/",
        InvoiceDetailView.as_view(),
        name="invoice-detail",
    ),
    path(
        "invoices/<int:pk>/download/",
        InvoicePDFDownloadView.as_view(),
        name="invoice-pdf-download",
    ),
]