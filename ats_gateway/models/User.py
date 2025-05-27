import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from .UserManager import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for the ATS Gateway service.
    Uses email as the primary identifier instead of username.
    """
    email = models.EmailField(primary_key=True, unique=True)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # Override PermissionsMixin fields to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='ats_gateway_user_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='ats_gateway_user_set',
        related_query_name='user',
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email 