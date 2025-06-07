from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class UserConfiguration(models.Model):
    id = models.AutoField(primary_key=True)
    
    # User reference - should reference User.public_id (UUID)
    user_id = models.UUIDField(unique=True, db_index=True, help_text='References User.public_id')
    
    # Risk management settings
    risk_appetite = models.FloatField(
        default=5.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Risk appetite percentage (0-100)'
    )
    min_reward_risk_ratio = models.FloatField(
        default=2.0, 
        validators=[MinValueValidator(0.1)],
        help_text='Minimum reward to risk ratio'
    )
    max_reward_risk_ratio = models.FloatField(
        default=20.0, 
        validators=[MinValueValidator(0.1)],
        help_text='Maximum reward to risk ratio'
    )
    
    # Trading session settings
    trades_per_session = models.IntegerField(
        default=100, 
        validators=[MinValueValidator(1)],
        help_text='Maximum trades per session'
    )
    max_daily_trades = models.IntegerField(
        default=500, 
        validators=[MinValueValidator(1)],
        help_text='Maximum trades per day'
    )
    
    # Position management
    max_position_size = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=100000.00,
        validators=[MinValueValidator(Decimal('1.00'))],
        help_text='Maximum position size in currency'
    )
    position_size_percentage = models.FloatField(
        default=10.0, 
        validators=[MinValueValidator(0.1), MaxValueValidator(100.0)],
        help_text='Position size as percentage of capital'
    )
    
    # Stop loss and take profit settings
    default_stop_loss_percentage = models.FloatField(
        default=2.0, 
        validators=[MinValueValidator(0.1), MaxValueValidator(50.0)],
        help_text='Default stop loss percentage'
    )
    default_take_profit_percentage = models.FloatField(
        default=4.0, 
        validators=[MinValueValidator(0.1), MaxValueValidator(100.0)],
        help_text='Default take profit percentage'
    )
    
    # Status and metadata
    is_active = models.BooleanField(default=True, db_index=True, help_text='Whether configuration is active')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_configurations"
        verbose_name = "User Configuration"
        verbose_name_plural = "User Configurations"
        ordering = ['user_id']
        constraints = [
            models.CheckConstraint(
                check=models.Q(min_reward_risk_ratio__lte=models.F('max_reward_risk_ratio')),
                name='chk_reward_risk_ratio_order'
            ),
            models.CheckConstraint(
                check=models.Q(default_stop_loss_percentage__lte=models.F('default_take_profit_percentage')),
                name='chk_stop_loss_take_profit_order'
            ),
        ]

    def __str__(self):
        return f"Configuration for User {self.user_id}"

    @classmethod
    def get_attribute(cls, user_id, attribute):
        """Legacy method for backward compatibility"""
        try:
            user_config = cls.objects.get(user_id=user_id, is_active=True)
            return getattr(user_config, attribute, None)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_or_create_for_user(cls, user_id, **kwargs):
        """Get or create configuration for a user with default values"""
        defaults = {
            'risk_appetite': 5.0,
            'min_reward_risk_ratio': 2.0,
            'max_reward_risk_ratio': 20.0,
            'trades_per_session': 100,
            'max_daily_trades': 500,
            'max_position_size': Decimal('100000.00'),
            'position_size_percentage': 10.0,
            'default_stop_loss_percentage': 2.0,
            'default_take_profit_percentage': 4.0,
            'is_active': True,
        }
        defaults.update(kwargs)
        
        return cls.objects.get_or_create(
            user_id=user_id,
            defaults=defaults
        )

    @classmethod
    def get_active_config(cls, user_id):
        """Get active configuration for a user"""
        try:
            return cls.objects.get(user_id=user_id, is_active=True)
        except cls.DoesNotExist:
            return None

    def update_configuration(self, **kwargs):
        """Update configuration with validation"""
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        
        # Trigger full_clean to run validators and constraints
        self.full_clean()
        self.save()
