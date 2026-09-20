from django.contrib.auth.models import User
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    REQUESTER = "REQUESTER", "Requester"
    APPROVER1 = "APPROVER1", "Approver 1"
    APPROVER2 = "APPROVER2", "Approver 2"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REQUESTER)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == Role.ADMIN or self.user.is_superuser

    @property
    def is_requester(self):
        return self.role == Role.REQUESTER or self.is_admin

    @property
    def is_approver1(self):
        return self.role == Role.APPROVER1 or self.is_admin

    @property
    def is_approver2(self):
        return self.role == Role.APPROVER2 or self.is_admin
