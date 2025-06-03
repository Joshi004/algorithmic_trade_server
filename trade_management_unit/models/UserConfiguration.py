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

    def calculate_position_size(self, account_balance, instrument_price):
        """Calculate position size based on configuration and account balance"""
        # Calculate based on percentage of capital
        max_amount_percentage = (account_balance * self.position_size_percentage) / 100
        
        # Calculate based on absolute maximum
        max_amount_absolute = float(self.max_position_size)
        
        # Use the smaller of the two
        max_amount = min(max_amount_percentage, max_amount_absolute)
        
        # Calculate quantity (number of shares/units)
        if instrument_price > 0:
            quantity = int(max_amount / instrument_price)
            return max(1, quantity)  # At least 1 unit
        return 1

    def calculate_stop_loss_price(self, entry_price, trade_direction='long'):
        """Calculate stop loss price based on configuration"""
        stop_loss_factor = self.default_stop_loss_percentage / 100
        
        if trade_direction.lower() == 'long':
            return entry_price * (1 - stop_loss_factor)
        else:  # short
            return entry_price * (1 + stop_loss_factor)

    def calculate_take_profit_price(self, entry_price, trade_direction='long'):
        """Calculate take profit price based on configuration"""
        take_profit_factor = self.default_take_profit_percentage / 100
        
        if trade_direction.lower() == 'long':
            return entry_price * (1 + take_profit_factor)
        else:  # short
            return entry_price * (1 - take_profit_factor)

    def is_within_reward_risk_ratio(self, reward_risk_ratio):
        """Check if a given reward-risk ratio is within configured limits"""
        return self.min_reward_risk_ratio <= reward_risk_ratio <= self.max_reward_risk_ratio

    def validate_trade_limits(self, current_session_trades=0, current_daily_trades=0):
        """Validate if more trades can be taken based on limits"""
        session_limit_ok = current_session_trades < self.trades_per_session
        daily_limit_ok = current_daily_trades < self.max_daily_trades
        
        return {
            'can_trade': session_limit_ok and daily_limit_ok,
            'session_limit_reached': not session_limit_ok,
            'daily_limit_reached': not daily_limit_ok,
            'session_trades_remaining': max(0, self.trades_per_session - current_session_trades),
            'daily_trades_remaining': max(0, self.max_daily_trades - current_daily_trades),
        }

    def update_configuration(self, **kwargs):
        """Update configuration with validation"""
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        
        # Trigger full_clean to run validators and constraints
        self.full_clean()
        self.save()

    @property
    def risk_level(self):
        """Get risk level description based on risk appetite"""
        if self.risk_appetite <= 20:
            return 'Conservative'
        elif self.risk_appetite <= 50:
            return 'Moderate'
        elif self.risk_appetite <= 80:
            return 'Aggressive'
        else:
            return 'Very Aggressive'
