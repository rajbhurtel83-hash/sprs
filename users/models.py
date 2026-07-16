from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class User(AbstractUser):
    """Custom user model with role-based access."""

    class Role(models.TextChoices):
        TENANT = 'tenant', 'Tenant'
        OWNER = 'owner', 'Property Owner'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.TENANT,
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\d{10}$', 'Phone number must be exactly 10 digits.')],
    )
    address = models.CharField(max_length=255, blank=True)
    deactivation_reason = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def clean(self):
        super().clean()

        if self.phone:
            phone = self.phone.strip()
            if not phone.isdigit() or len(phone) != 10:
                raise ValidationError({'phone': 'Phone number must be exactly 10 digits.'})
            self.phone = phone

    @property
    def is_tenant(self):
        return self.role == self.Role.TENANT

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser
