import os
import resend

from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema

from .models import CustomUser
from .serializers import (
    UserSerializer,
    UserLoginSerializer,
    UserUpdateSerializer,
)


@extend_schema(tags=["Authentication"])
class UserSignUp(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(tags=["Authentication"])
class VerifyEmail(generics.GenericAPIView):
    serializer_class = UserSerializer
    swagger_fake_view = True

    def get(self, request, token):
        user = CustomUser.objects.filter(
            verification_token=token
        ).first()

        if user:
            if user.is_verified:
                return Response(
                    {"details": "Email already verified!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.is_verified = True
            user.verification_token = None
            user.save()

            return Response(
                {"details": "Successfully verified!"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"details": "Invalid token"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Authentication"])
class ResendVerificationEmail(generics.GenericAPIView):
    serializer_class = UserSerializer
    swagger_fake_view = True

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")

        if not email:
            return Response(
                {"details": "Email is required!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = CustomUser.objects.filter(email=email).first()

        if not user:
            return Response(
                {"details": "User with this email doesn't exist!"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_verified:
            return Response(
                {"details": "Email already verified!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.verification_token = get_random_string(length=32)
        user.save()

        verification_link = request.build_absolute_uri(
            reverse(
                "verify_email",
                kwargs={"token": user.verification_token},
            )
        )

        html_content = render_to_string(
            "emails/verification_email.html",
            {
                "user": user.username,
                "verification_link": verification_link,
            },
        )

        resend.api_key = os.getenv("RESEND_API_KEY")

        resend.Emails.send(
            {
                "from": "onboarding@resend.dev",
                "to": [user.email],
                "subject": "Verify your email",
                "html": html_content,
            }
        )

        return Response(
            {"details": "Verification email sent!"},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class UserLogin(generics.GenericAPIView):
    serializer_class = UserLoginSerializer

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = CustomUser.objects.filter(email=email).first()

        if user and user.check_password(password):
            if not user.is_verified:
                return Response(
                    {"details": "Email is not verified yet!"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "refresh_token": str(refresh),
                    "access_token": str(refresh.access_token),
                }
            )

        return Response(
            {"details": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@extend_schema(tags=["Profile"])
class RetrieveUpdateProfile(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return UserUpdateSerializer

        return UserSerializer