from django.urls import path

from .views import (
    PaymentListView,
    PaymentDetailView,
    PaymentCreateView,
    PaymentStatusUpdateView,
    PaymentWebhookView,
    SSLCommerzSuccessView,
    SSLCommerzFailView,
    SSLCommerzCancelView,
    SSLCommerzIPNView,
)

urlpatterns = [
    path("", PaymentListView.as_view(), name="payment-list"),
    path("create/", PaymentCreateView.as_view(), name="payment-create"),
    path("<int:pk>/status/", PaymentStatusUpdateView.as_view(), name="payment-status-update"),
    path("webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
    path("sslcommerz/success/", SSLCommerzSuccessView.as_view(), name="sslcommerz-success"),
    path("sslcommerz/fail/", SSLCommerzFailView.as_view(), name="sslcommerz-fail"),
    path("sslcommerz/cancel/", SSLCommerzCancelView.as_view(), name="sslcommerz-cancel"),
    path("sslcommerz/ipn/", SSLCommerzIPNView.as_view(), name="sslcommerz-ipn"),
    path("<int:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
]