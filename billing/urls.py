from django.urls import path
from .views import InvoiceListView, InvoiceDetailView


urlpatterns = [
    path("invoices/", InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
]