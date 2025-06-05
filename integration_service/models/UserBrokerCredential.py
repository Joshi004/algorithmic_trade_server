from django.db import models
from django_mysql.models import EnumField
from django.utils import timezone
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from django.db import transaction
import uuid
from datetime import date, timedelta


class UserBrokerCredential(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False)
    
    # User reference - UUID field referencing User.public_id
    user_id = models.UUIDField(
        blank=False, 
        db_index=True,
        help_text="References User.public_id"
    )
    
    # Broker configuration
    BROKER_CHOICES = [
        ("zerodha", "zerodha"), 
        ("upstox", "upstox"), 
        ("angel", "angel")
    ]
    broker_name = EnumField(
        choices=BROKER_CHOICES,
        default="zerodha",
        db_index=True,
        help_text="Broker name for integration"
    )
    
    # API credentials - should be encrypted in practice
    api_key = models.CharField(
        max_length=255, 
        blank=False,
        validators=[MinLengthValidator(10)],
        help_text="Broker API key"
    )
    api_secret = models.CharField(
        max_length=255, 
        blank=False,
        validators=[MinLengthValidator(10)],
        help_text="Broker API secret"
    )
    
    # Token management
    access_token = models.CharField(
        max_length=512, 
        blank=True, 
        null=True,
        help_text="Current access token from broker"
    )
    refresh_token = models.CharField(
        max_length=512, 
        blank=True, 
        null=True,
        help_text="Refresh token for access token renewal"
    )
    public_token = models.CharField(
        max_length=512, 
        blank=True, 
        null=True,
        help_text="Public token from broker (encrypted)"
    )
    
    # Credential status
    STATUS_CHOICES = [
        ("active", "active"), 
        ("revoked", "revoked"), 
        ("expired", "expired"),
        ("pending_verification", "pending_verification"),
        ("invalid", "invalid")
    ]
    status = EnumField(
        choices=STATUS_CHOICES,
        default="pending_verification",
        db_index=True,
        help_text="Current status of the credential"
    )
    
    # Account management
    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this is the default credential for the user"
    )
    is_paper_trading = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this credential is for paper trading"
    )
    
    # Validation and monitoring
    last_validated_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="When the credentials were last validated"
    )
    validation_error = models.TextField(
        blank=True, 
        null=True,
        help_text="Last validation error message if any"
    )
    last_used_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="When the credentials were last used for trading"
    )
    
    # Kite specific fields
    kite_user_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="User ID from Kite/Zerodha (e.g. OOD246)"
    )
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_broker_credentials"
        verbose_name = "User Broker Credential"
        verbose_name_plural = "User Broker Credentials"
        ordering = ['user_id', '-is_default', 'broker_name']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['broker_name']),
            models.Index(fields=['status']),
            models.Index(fields=['is_default']),
            models.Index(fields=['is_paper_trading']),
            models.Index(fields=['user_id', 'broker_name']),
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['kite_user_id']),
        ]

    def __str__(self):
        return f"{self.broker_name.title()} credentials for User {self.user_id}"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate API key/secret format based on broker
        if self.broker_name == 'zerodha':
            if len(self.api_key) < 15:
                raise ValidationError({'api_key': 'Zerodha API key should be at least 15 characters'})

    @classmethod
    def create_broker_credential(cls, user_id, broker_name, api_key, api_secret, is_paper_trading=False):
        """
        Create a new broker credential for a user
        """
        with transaction.atomic():
            # Check if this is the first credential for this user/broker combination
            is_first = not cls.objects.filter(user_id=user_id, broker_name=broker_name).exists()
            
            # Create the new credential
            credential = cls(
                user_id=user_id,
                broker_name=broker_name,
                api_key=api_key,
                api_secret=api_secret,
                is_default=is_first,  # Set as default if it's the first one for this broker
                is_paper_trading=is_paper_trading
            )
            credential.full_clean()
            credential.save()
            return credential

    @classmethod
    def set_as_default(cls, credential_id, user_id):
        """
        Set a specific credential as the default for a user
        """
        with transaction.atomic():
            credential = cls.objects.get(id=credential_id, user_id=user_id)
            
            # First, unset default for all credentials of this user for this broker
            cls.objects.filter(
                user_id=user_id, 
                broker_name=credential.broker_name
            ).update(is_default=False)
            
            # Then set the specified credential as default
            credential.is_default = True
            credential.save()
            return credential

    @classmethod
    def get_default_credential(cls, user_id, broker_name=None, is_paper_trading=None):
        """
        Get the default credential for a user, optionally filtered by broker and trading mode.
        Returns default credential regardless of status - validation happens during API calls.
        """
        query = cls.objects.filter(user_id=user_id, is_default=True)
        
        if broker_name:
            query = query.filter(broker_name=broker_name)
        if is_paper_trading is not None:
            query = query.filter(is_paper_trading=is_paper_trading)
        
        try:
            return query.get()
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # If multiple defaults found, return the most recently created
            return query.order_by('-created_at').first()

    @classmethod
    def get_active_credentials(cls, user_id, broker_name=None):
        """
        Get all active credentials for a user
        """
        query = cls.objects.filter(user_id=user_id, status='active')
        if broker_name:
            query = query.filter(broker_name=broker_name)
        return query.order_by('-is_default', 'broker_name')

    def validate_and_update_status(self, validation_result=None, error_message=None):
        """
        Update credential status based on validation result
        """
        self.last_validated_at = timezone.now()
        
        if validation_result:
            self.status = 'active'
            self.validation_error = None
        else:
            self.status = 'invalid'
            self.validation_error = error_message
        
        self.save(update_fields=['status', 'last_validated_at', 'validation_error', 'updated_at'])

    def update_token(self, access_token, refresh_token=None, public_token=None, kite_user_id=None):
        """
        Update access token and related information
        """
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        if public_token:
            self.public_token = public_token
        if kite_user_id:
            self.kite_user_id = kite_user_id
        
        self.last_used_at = timezone.now()
        self.save(update_fields=['access_token', 'refresh_token', 'public_token', 'kite_user_id', 'last_used_at', 'updated_at'])

    @property
    def is_healthy(self):
        """
        Check if credential is in a healthy state for trading
        """
        return self.status == 'active'

    def deactivate(self, reason="Manual deactivation"):
        """
        Deactivate the credential
        """
        self.status = 'revoked'
        self.validation_error = reason
        self.save(update_fields=['status', 'validation_error', 'updated_at'])

    @classmethod
    def cleanup_expired_tokens(cls):
        """
        Clean up expired tokens - utility method for maintenance
        Note: This method is kept for compatibility but tokens don't expire automatically anymore
        """
        return 0 