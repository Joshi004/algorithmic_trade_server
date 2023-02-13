
from  django.contrib.auth.models import BaseUserManager



class UserProfileManager(BaseUserManager):
    """Manager for user profiles"""
    
    def create_user(self,email,name,password=None):
        """Craetes a nwe user proile"""
        if (not email):
            raise ValueError("User must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email,name=name)
        user.set_password(password) #Converts Tp a hash inbuilt function
        user.save(using=self._db)
        return user
    
    def create_super_user(self,email,name,password):
        """Create and save new super user with given details"""
        user = self.create_user(email,name,password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


