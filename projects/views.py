from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Project
from .serializers import ProjectSerializer
from usage.services import check_project_limit, increment_projects_count, decrement_projects_count


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        check_project_limit(self.request.user)
        serializer.save(user=self.request.user)
        increment_projects_count(self.request.user)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        decrement_projects_count(user)