from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .serializers import UsageRecordSerializer
from .services import get_current_usage
from .permissions import TrackAPIUsage

@extend_schema(tags=["Usage"])
class CurrentUsageView(generics.RetrieveAPIView):
    serializer_class = UsageRecordSerializer
    permission_classes = [IsAuthenticated, TrackAPIUsage]

    def get_object(self):
        return get_current_usage(self.request.user)