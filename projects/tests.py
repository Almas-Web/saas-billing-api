from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from account.models import CustomUser
from subscriptions.models import Plan, Subscription
from usage.models import UsageRecord

from .models import Project


class ProjectTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            is_verified=True,
        )

        self.other_user = CustomUser.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="TestPassword123",
            is_verified=True,
        )

        self.plan = Plan.objects.create(
            name="Basic",
            price="10.00",
            billing_cycle="monthly",
            max_projects=3,
            max_api_requests=100,
            storage_limit_gb="1.00",
            is_active=True,
        )

        self.subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
        )

        self.project = Project.objects.create(
            user=self.user,
            name="Test Project",
            description="Test project description",
        )

        self.list_url = reverse("project-list-create")

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.user
        )

    def create_usage(self, projects_count=0):
        now = timezone.now()

        return UsageRecord.objects.create(
            user=self.user,
            plan=self.plan,
            api_requests=0,
            projects_count=projects_count,
            storage_used_gb="0.00",
            period_start=now.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            ),
            period_end=now.replace(
                day=28,
                hour=23,
                minute=59,
                second=59,
                microsecond=999999,
            ),
        )

    def test_authenticated_user_can_list_projects(self):
        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)

        self.assertEqual(
            response.data[0]["name"],
            "Test Project",
        )

    def test_unauthenticated_user_cannot_list_projects(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_create_project(self):
        self.authenticate()

        response = self.client.post(
            self.list_url,
            {
                "name": "New Project",
                "description": "New project description",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Project.objects.filter(
                user=self.user,
                name="New Project",
            ).exists()
        )

    def test_created_project_belongs_to_authenticated_user(self):
        self.authenticate()

        response = self.client.post(
            self.list_url,
            {
                "name": "Owned Project",
                "description": "Owned by user",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        project = Project.objects.get(
            name="Owned Project"
        )

        self.assertEqual(
            project.user,
            self.user,
        )

    def test_project_count_increases_after_creation(self):
        usage = self.create_usage(
            projects_count=1
        )

        self.authenticate()

        response = self.client.post(
            self.list_url,
            {
                "name": "Second Project",
                "description": "Second project",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        usage.refresh_from_db()

        actual_count = Project.objects.filter(
            user=self.user
        ).count()

        self.assertEqual(
            actual_count,
            2,
        )

        self.assertEqual(
            usage.projects_count,
            actual_count,
        )

    def test_user_cannot_create_project_after_limit_reached(self):
        Project.objects.create(
            user=self.user,
            name="Project 2",
        )

        Project.objects.create(
            user=self.user,
            name="Project 3",
        )

        self.authenticate()

        response = self.client.post(
            self.list_url,
            {
                "name": "Project 4",
                "description": "Should fail",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertFalse(
            Project.objects.filter(
                user=self.user,
                name="Project 4",
            ).exists()
        )

    def test_project_limit_does_not_affect_other_user(self):
        Project.objects.create(
            user=self.user,
            name="Project 2",
        )

        Project.objects.create(
            user=self.user,
            name="Project 3",
        )

        Subscription.objects.create(
            user=self.other_user,
            plan=self.plan,
            status="active",
        )

        self.authenticate(self.other_user)

        response = self.client.post(
            self.list_url,
            {
                "name": "Other User Project",
                "description": "Other user's project",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_user_only_sees_own_projects(self):
        Project.objects.create(
            user=self.other_user,
            name="Other User Project",
        )

        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        project_names = [
            project["name"]
            for project in response.data
        ]

        self.assertIn(
            "Test Project",
            project_names,
        )

        self.assertNotIn(
            "Other User Project",
            project_names,
        )

    def test_user_can_retrieve_own_project(self):
        self.authenticate()

        url = reverse(
            "project-detail",
            kwargs={"pk": self.project.pk},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["name"],
            "Test Project",
        )

    def test_user_cannot_retrieve_other_users_project(self):
        other_project = Project.objects.create(
            user=self.other_user,
            name="Other Project",
        )

        self.authenticate()

        url = reverse(
            "project-detail",
            kwargs={"pk": other_project.pk},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_can_update_own_project(self):
        self.authenticate()

        url = reverse(
            "project-detail",
            kwargs={"pk": self.project.pk},
        )

        response = self.client.patch(
            url,
            {
                "name": "Updated Project",
                "description": "Updated description",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.project.refresh_from_db()

        self.assertEqual(
            self.project.name,
            "Updated Project",
        )

        self.assertEqual(
            self.project.description,
            "Updated description",
        )

    def test_user_cannot_update_other_users_project(self):
        other_project = Project.objects.create(
            user=self.other_user,
            name="Other Project",
        )

        self.authenticate()

        url = reverse(
            "project-detail",
            kwargs={"pk": other_project.pk},
        )

        response = self.client.patch(
            url,
            {
                "name": "Hacked Project",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        other_project.refresh_from_db()

        self.assertEqual(
            other_project.name,
            "Other Project",
        )

    def test_user_can_delete_own_project(self):
        self.authenticate()

        url = reverse(
            "project-detail",
            kwargs={"pk": self.project.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Project.objects.filter(
                pk=self.project.pk
            ).exists()
        )

    def test_project_count_decreases_after_delete(self):
        usage = self.create_usage(
            projects_count=1
        )

        self.authenticate()

        url = reverse(
            "project-detail",
            kwargs={"pk": self.project.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        usage.refresh_from_db()

        self.assertEqual(
            usage.projects_count,
            0,
        )

    def test_user_cannot_delete_other_users_project(self):
        other_project = Project.objects.create(
            user=self.other_user,
            name="Other Project",
        )

        self.authenticate()

        url = reverse(
            "project-detail",
            kwargs={"pk": other_project.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(
            Project.objects.filter(
                pk=other_project.pk
            ).exists()
        )

    def test_duplicate_project_name_for_same_user_is_not_allowed(self):
        self.authenticate()

        response = self.client.post(
            self.list_url,
            {
                "name": "Test Project",
                "description": "Duplicate",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            Project.objects.filter(
                user=self.user,
                name="Test Project",
            ).count(),
            1,
        )

    def test_same_project_name_for_different_users_is_allowed(self):
        project = Project.objects.create(
            user=self.other_user,
            name="Test Project",
        )

        self.assertIsNotNone(
            project.pk
        )

        self.assertEqual(
            Project.objects.filter(
                name="Test Project"
            ).count(),
            2,
        )

    def test_project_description_is_optional(self):
        self.authenticate()

        response = self.client.post(
            self.list_url,
            {
                "name": "No Description Project",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        project = Project.objects.get(
            name="No Description Project"
        )

        self.assertEqual(
            project.description,
            "",
        )

    def test_project_id_is_read_only(self):
        self.authenticate()

        original_id = self.project.id

        url = reverse(
            "project-detail",
            kwargs={"pk": self.project.pk},
        )

        response = self.client.patch(
            url,
            {
                "id": 9999,
                "name": "Changed Name",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.project.refresh_from_db()

        self.assertEqual(
            self.project.id,
            original_id,
        )

    def test_created_at_and_updated_at_are_read_only(self):
        self.authenticate()

        original_created_at = self.project.created_at

        url = reverse(
            "project-detail",
            kwargs={"pk": self.project.pk},
        )

        response = self.client.patch(
            url,
            {
                "name": "Updated Timestamp Test",
                "created_at": "2020-01-01T00:00:00Z",
                "updated_at": "2020-01-01T00:00:00Z",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.project.refresh_from_db()

        self.assertEqual(
            self.project.created_at,
            original_created_at,
        )

    def test_project_list_is_ordered_by_created_at(self):
        Project.objects.create(
            user=self.user,
            name="Second Project",
        )

        Project.objects.create(
            user=self.user,
            name="Third Project",
        )

        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        project_names = [
            project["name"]
            for project in response.data
        ]

        self.assertEqual(
            len(project_names),
            3,
        )

        self.assertEqual(
            project_names[0],
            "Third Project",
        )

        self.assertEqual(
            project_names[1],
            "Second Project",
        )

        self.assertEqual(
            project_names[2],
            "Test Project",
        )

    def test_project_string_representation(self):
        self.assertEqual(
            str(self.project),
            "testuser - Test Project",
        )

    def test_unauthenticated_user_cannot_create_project(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Unauthorized Project",
                "description": "Should fail",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_user_cannot_update_project(self):
        url = reverse(
            "project-detail",
            kwargs={"pk": self.project.pk},
        )

        response = self.client.patch(
            url,
            {
                "name": "Unauthorized Update",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_user_cannot_delete_project(self):
        url = reverse(
            "project-detail",
            kwargs={"pk": self.project.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )