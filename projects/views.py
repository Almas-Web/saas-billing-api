from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import Project
from .serializers import ProjectSerializer
from usage.services import check_project_limit, update_projects_count

@extend_schema(tags=["Projects"])
class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        check_project_limit(user)
        serializer.save(user=user)
        actual_count = Project.objects.filter(user=user).count()
        update_projects_count(user, actual_count)

@extend_schema(tags=["Projects"])
class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        actual_count = Project.objects.filter(user=user).count()
        update_projects_count(user, actual_count)