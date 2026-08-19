from django.urls import path

from .views import CurrentUsageView


urlpatterns = [
    path(
        "current/",
        CurrentUsageView.as_view(),
        name="current-usage"
    ),
]