from unittest.mock import patch

from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from .models import CustomUser


class AccountTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            is_verified=True,
        )

    def test_user_registration(self):
        with patch("account.serializers.resend.Emails.send") as mock_send:
            response = self.client.post(
                reverse("signup"),
                {
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password": "NewPassword123",
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = CustomUser.objects.get(
            email="newuser@example.com"
        )

        self.assertEqual(user.username, "newuser")
        self.assertFalse(user.is_verified)
        self.assertIsNotNone(user.verification_token)
        mock_send.assert_called_once()

    def test_password_is_hashed(self):
        with patch("account.serializers.resend.Emails.send"):
            self.client.post(
                reverse("signup"),
                {
                    "username": "hashuser",
                    "email": "hash@example.com",
                    "password": "Password123",
                },
                format="json",
            )

        user = CustomUser.objects.get(
            email="hash@example.com"
        )

        self.assertNotEqual(
            user.password,
            "Password123",
        )

        self.assertTrue(
            user.check_password("Password123")
        )

    def test_registration_sends_verification_email(self):
        with patch(
            "account.serializers.resend.Emails.send"
        ) as mock_send:
            response = self.client.post(
                reverse("signup"),
                {
                    "username": "emailuser",
                    "email": "email@example.com",
                    "password": "Password123",
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        mock_send.assert_called_once()

    def test_email_verification(self):
        user = CustomUser.objects.create_user(
            username="verifyuser",
            email="verify@example.com",
            password="Password123",
            is_verified=False,
            verification_token="abc123",
        )

        response = self.client.get(
            reverse(
                "verify_email",
                kwargs={
                    "token": user.verification_token
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        user.refresh_from_db()

        self.assertTrue(user.is_verified)
        self.assertIsNone(user.verification_token)

    def test_invalid_verification_token(self):
        response = self.client.get(
            reverse(
                "verify_email",
                kwargs={
                    "token": "invalid-token"
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_already_verified_email(self):
        user = CustomUser.objects.create_user(
            username="alreadyverified",
            email="already@example.com",
            password="Password123",
            is_verified=True,
            verification_token="already-token",
        )

        response = self.client.get(
            reverse(
                "verify_email",
                kwargs={
                    "token": user.verification_token
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch("account.views.resend.Emails.send")
    def test_resend_verification_email(self, mock_send):
        user = CustomUser.objects.create_user(
            username="resenduser",
            email="resend@example.com",
            password="Password123",
            is_verified=False,
            verification_token="old-token",
        )

        response = self.client.post(
            reverse("resend_verification"),
            {"email": user.email},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        user.refresh_from_db()

        self.assertIsNotNone(
            user.verification_token
        )

        self.assertNotEqual(
            user.verification_token,
            "old-token",
        )

        mock_send.assert_called_once()

    def test_resend_verification_without_email(self):
        response = self.client.post(
            reverse("resend_verification"),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_resend_verification_for_nonexistent_user(self):
        response = self.client.post(
            reverse("resend_verification"),
            {
                "email": "doesnotexist@example.com"
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_resend_verification_for_verified_user(self):
        response = self.client.post(
            reverse("resend_verification"),
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_login(self):
        response = self.client.post(
            reverse("login"),
            {
                "email": self.user.email,
                "password": "TestPassword123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "access_token",
            response.data,
        )

        self.assertIn(
            "refresh_token",
            response.data,
        )

    def test_login_with_wrong_password(self):
        response = self.client.post(
            reverse("login"),
            {
                "email": self.user.email,
                "password": "WrongPassword123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_login_with_unverified_email(self):
        user = CustomUser.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password="Password123",
            is_verified=False,
        )

        response = self.client.post(
            reverse("login"),
            {
                "email": user.email,
                "password": "Password123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_view_profile(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            reverse("profile")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["username"],
            self.user.username,
        )

    def test_unauthenticated_user_cannot_view_profile(self):
        response = self.client.get(
            reverse("profile")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_can_update_profile(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.patch(
            reverse("profile"),
            {
                "bio": "Python Backend Developer"
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.bio,
            "Python Backend Developer",
        )

    def test_refresh_token(self):
        login_response = self.client.post(
            reverse("login"),
            {
                "email": self.user.email,
                "password": "TestPassword123",
            },
            format="json",
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        refresh_token = login_response.data[
            "refresh_token"
        ]

        response = self.client.post(
            reverse("token_refresh"),
            {
                "refresh": refresh_token
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "access",
            response.data,
        )