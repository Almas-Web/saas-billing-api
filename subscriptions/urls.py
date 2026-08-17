from django.urls import path

from .views import PlanListCreateView, PlanDetailView, SubscribeView, SubscriptionDetailView, SubscriptionListView

urlpatterns = [
    path("plans/", PlanListCreateView.as_view(), name="plan-list-create"),
    path("plans/<int:pk>/", PlanDetailView.as_view(), name="plan-detail"),
    path("subscriptions/", SubscriptionListView.as_view(), name="subscription-list"),
    path("subscriptions/<int:pk>/", SubscriptionDetailView.as_view(), name="subscription-detail"),
    path("subscriptions/subscribe/", SubscribeView.as_view(), name="subscribe"),
]