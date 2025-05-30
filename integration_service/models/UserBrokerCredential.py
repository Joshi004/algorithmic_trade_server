from django.db import models
from django_mysql.models import EnumField
from django.utils import timezone
import uuid

class UserBrokerCredential(models.Model):
    class Meta:
        db_table = "user_broker_credentials"
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['broker_name']),
            models.Index(fields=['status']),
        ]
    
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False)
    # This field stores the UUID from User.public_id
    user_id = models.UUIDField(blank=False, help_text="References User.public_id")
    
    BROKER_CHOICES = [("zerodha", "zerodha")]
    broker_name = EnumField(choices=BROKER_CHOICES, default="zerodha")
    
    api_key = models.CharField(max_length=255, blank=False)
    api_secret = models.CharField(max_length=255, blank=False)
    access_token = models.CharField(max_length=255, blank=True, null=True)
    refresh_token = models.CharField(max_length=255, blank=True, null=True)
    token_expiry = models.DateTimeField(blank=True, null=True)
    
    STATUS_CHOICES = [("active", "active"), ("revoked", "revoked"), ("expired", "expired")]
    status = EnumField(choices=STATUS_CHOICES, default="active")
    
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    @classmethod
    def create_broker_credential(cls, user_id, broker_name, api_key, api_secret):
        """
        Create a new broker credential for a user
        """
        # Check if this is the first credential for this user
        is_first = not cls.objects.filter(user_id=user_id).exists()
        
        # Create the new credential
        credential = cls(
            user_id=user_id,
            broker_name=broker_name,
            api_key=api_key,
            api_secret=api_secret,
            is_default=is_first  # Set as default if it's the first one
        )
        credential.save()
        return credential
    
    @classmethod
    def set_as_default(cls, credential_id, user_id):
        """
        Set a specific credential as the default for a user
        """
        # First, unset default for all credentials of this user
        cls.objects.filter(user_id=user_id).update(is_default=False)
        
        # Then set the specified credential as default
        credential = cls.objects.get(id=credential_id, user_id=user_id)
        credential.is_default = True
        credential.save()
        return credential
    
    @classmethod
    def get_default_credential(cls, user_id, broker_name=None):
        """
        Get the default credential for a user, optionally filtered by broker
        """
        query = cls.objects.filter(user_id=user_id, is_default=True)
        if broker_name:
            query = query.filter(broker_name=broker_name)
        
        try:
            return query.get()
        except cls.DoesNotExist:
            return None 