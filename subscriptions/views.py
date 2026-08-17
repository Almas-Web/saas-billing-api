from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Plan, Subscription
from .serializers import PlanSerializer, SubscribeSerializer, SubscriptionSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
class PlanListCreateView(generics.ListCreateAPIView):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return []
class PlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsAdminUser]

class SubscriptionListView(generics.ListAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)
class SubscriptionDetailView(generics.RetrieveAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

class SubscribeView(generics.CreateAPIView):
    serializer_class = SubscribeSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data["plan_id"]

        subscription = Subscription.objects.filter(
            user=request.user,
            status="active"
        ).first()

        if subscription:
            return Response({
                "details": "You already have an active subscription."
            }, status=status.HTTP_400_BAD_REQUEST)

        subscription = Subscription.objects.create(
            user=request.user,
            plan=plan
        )

        return Response(
            SubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED
        )