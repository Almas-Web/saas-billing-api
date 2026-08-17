from django.utils.crypto import get_random_string
from rest_framework import serializers
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .models import CustomUser
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'bio', 'image']
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
            reverse('verify_email', kwargs={'token': user.verification_token}))

        subject = 'Verify your email'
        html_content = render_to_string('emails/verification_email.html', {
            'user': user.username,
            'verification_link': verification_link})

        email = EmailMultiAlternatives(
            subject,
            'Please verify your email address.',
            None,
            [user.email] )

        email.attach_alternative(html_content, 'text/html')
        email.send(fail_silently=False)

        return True


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['bio', 'image']

    def update(self, instance, validated_data):
        instance.bio = validated_data.get('bio', instance.bio)
        instance.image = validated_data.get('image', instance.image)
        instance.save()
        return instance