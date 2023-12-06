from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from .user_profile_mnager import UserProfileManager



class UserProfile(AbstractBaseUser,PermissionsMixin):
    """Database model fro users in the system"""    
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=225)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    objects = UserProfileManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def get_full_name(self):
        """Retrieve Full name of the user"""
        return self.name
    
    def get_short_name(self):
        """Retrive short name of the user"""
        return self.name

    def __str__(self):
        """return String representation of user"""
        return self.email
