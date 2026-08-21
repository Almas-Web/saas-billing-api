import os
import resend
from django.utils.crypto import get_random_string
from rest_framework import serializers
from django.urls import reverse
from django.template.loader import render_to_string
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'bio']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser(**validated_data)
        user.set_password(validated_data['password'])
        user.verification_token = get_random_string(length=32)
        user.save()
        self.send_email(user)
        return user

    def send_email(self, user):
        verification_link = self.context['request'].build_absolute_uri(
            reverse('verify_email', kwargs={'token': user.verification_token})
        )
        html_content = render_to_string('emails/verification_email.html', {'user': user.username, 'verification_link': verification_link})
        resend.api_key = os.getenv('RESEND_API_KEY')
        resend.Emails.send({'from': 'onboarding@resend.dev', 'to': [user.email], 'subject': 'Verify your email', 'html': html_content})
        return True

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['bio']

    def update(self, instance, validated_data):
        instance.bio = validated_data.get('bio', instance.bio)
        instance.save()
        return instance