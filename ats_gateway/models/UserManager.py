import re
import bcrypt
from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError


def validate_password(password):
    """
    Validate password against security requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 numeric digit
    - At least 1 special character
    """
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    
    if not re.search(r'[0-9]', password):
        raise ValidationError("Password must contain at least one numeric digit.")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character.")
    
    return True


class UserManager(BaseUserManager):
    """
    Custom manager for the User model.
    """
    
    def create_user(self, email, password, **extra_fields):
        """
        Create a new user with the given email and password.
        """
        if not email:
            raise ValueError("Users must have an email address")
        
        # Normalize the email
        email = self.normalize_email(email)
        
        # Validate the password
        validate_password(password)
        
        # Create the user instance
        user = self.model(email=email, **extra_fields)
        
        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user.password = hashed_password.decode('utf-8')
        
        # Set is_active to True by default
        user.is_active = True
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password, **extra_fields):
        """
        Create a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields) 