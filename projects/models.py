from django.db import models
from django.conf import settings


class Project(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )

    name = models.CharField(
        max_length=150
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        unique_together = ("user", "name")

    def __str__(self):
        return f"{self.user.username} - {self.name}"