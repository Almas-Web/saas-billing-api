from django.urls import path
from .views import PaymentListView, PaymentDetailView, PaymentCreateView, PaymentStatusUpdateView, PaymentWebhookView

urlpatterns = [
    path("", PaymentListView.as_view(), name="payment-list"),
    path("create/", PaymentCreateView.as_view(), name="payment-create"),
    path("<int:pk>/status/", PaymentStatusUpdateView.as_view(), name="payment-status-update"),
    path("webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
    path("<int:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
]