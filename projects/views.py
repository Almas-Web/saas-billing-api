from django.db import transaction

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Project
from .serializers import ProjectSerializer

from usage.services import (
    check_project_limit,
    update_projects_count,
)


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            user=self.request.user
        )

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user

        # Check plan limit before creating project
        check_project_limit(user)

        # Create project
        serializer.save(user=user)

        # Sync usage count with actual project count
        actual_count = Project.objects.filter(
            user=user
        ).count()

        update_projects_count(
            user,
            actual_count
        )


class ProjectDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            user=self.request.user
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        user = instance.user

        # Delete project
        instance.delete()

        # Sync usage count with actual project count
        actual_count = Project.objects.filter(
            user=user
        ).count()

        update_projects_count(
            user,
            actual_count
        )