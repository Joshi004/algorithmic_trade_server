from django.db import models
from django_mysql.models import EnumField
from django.db.models import Sum
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from ats_gateway.models.User import User
from decimal import Decimal
from trade_management_unit.lib.common.Utils.Utils import current_ist
from trade_management_unit.lib.common.Utils.custome_logger import log


class Trade(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False)
    
    # User reference - ForeignKey to User.public_id
    user_id = models.ForeignKey(
        User,
        to_field='public_id',
        on_delete=models.CASCADE,
        db_column='user_id',
        help_text='References User.public_id'
    )
    
    # Trade status and lifecycle
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether the trade is currently active'
    )
    started_at = models.DateTimeField(help_text='When the trade was initiated')
    closed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When the trade was closed'
    )
    
    # Trade relationships
    instrument = models.ForeignKey(
        "Instrument",
        on_delete=models.PROTECT,
        verbose_name="Ordered Instrument",
        help_text='The financial instrument being traded'
    )
    trade_session = models.ForeignKey(
        "TradeSession",
        on_delete=models.CASCADE,
        verbose_name="Trade Session",
        help_text='The trading session this trade belongs to'
    )
    
    # Trade direction and performance
    VIEW_CHOICES = [("long", "Long"), ("short", "Short")]
    view = EnumField(
        choices=VIEW_CHOICES,
        default="long",
        db_index=True,
        help_text='Trading direction: long (buy) or short (sell)'
    )
    net_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Net profit/loss for this trade'
    )
    
    # Trade metadata
    entry_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Price at which the trade was entered'
    )
    exit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Price at which the trade was exited'
    )
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of units traded'
    )
    stop_loss_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Stop loss price for risk management'
    )
    take_profit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Take profit price target'
    )
    
    # Trade execution details
    total_fees = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total fees and charges for this trade'
    )
    trade_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total value of the trade'
    )
    
    # Trade notes and status
    trade_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Notes or comments about this trade'
    )
    exit_reason = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Reason for trade exit (profit target, stop loss, manual, etc.)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trades"
        verbose_name = "Trade"
        verbose_name_plural = "Trades"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['started_at']),
            models.Index(fields=['closed_at']),
            models.Index(fields=['view']),
            models.Index(fields=['instrument']),
            models.Index(fields=['trade_session']),
            # Composite indexes
            models.Index(fields=['user_id', 'is_active']),
            models.Index(fields=['user_id', 'trade_session']),
            models.Index(fields=['trade_session', 'is_active']),
            models.Index(fields=['user_id', 'instrument']),
            models.Index(fields=['is_active', 'view']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(closed_at__isnull=True) | models.Q(closed_at__gte=models.F('started_at')),
                name='chk_trades_date_order'
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name='chk_trades_positive_quantity'
            ),
        ]

    def __str__(self):
        return f"Trade {self.id} - {self.instrument.trading_symbol} ({self.view})"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate that closed_at >= started_at
        if self.closed_at and self.started_at and self.closed_at < self.started_at:
            raise ValidationError({'closed_at': 'Trade close time cannot be before start time'})
        
        # Validate price consistency
        if self.entry_price and self.exit_price:
            if self.view == 'long' and self.exit_price <= 0:
                raise ValidationError({'exit_price': 'Exit price must be positive'})
            elif self.view == 'short' and self.exit_price <= 0:
                raise ValidationError({'exit_price': 'Exit price must be positive'})

    @classmethod
    def fetch_active_trade(cls, instrument_id, trade_session_id, user_id):
        """Fetch active trade for given parameters"""
        # Handle UUID string conversion
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                return None
        else:
            user = user_id
            
        try:
            return cls.objects.get(
                instrument_id=instrument_id,
                trade_session_id=trade_session_id,
                user_id=user,
                is_active=True
            )
        except cls.DoesNotExist:
            return None

    @classmethod
    def fetch_or_initiate_trade(cls, instrument_id, action, trade_session_id, user_id, entry_price=None, quantity=1):
        """Fetch existing trade or create new one"""
        # Handle UUID string conversion
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                return None, "User not found"
        else:
            user = user_id

        with transaction.atomic():
            trade, created = cls.objects.select_for_update().get_or_create(
                instrument_id=instrument_id,
                trade_session_id=trade_session_id,
                user_id=user,
                is_active=True,
                defaults={
                    'started_at': current_ist(),
                    'view': 'long' if action == 'buy' else 'short',
                    'entry_price': entry_price,
                    'quantity': quantity,
                }
            )
        return trade, "Created" if created else "Existing"

    @classmethod
    def initiate_trade(cls, instrument_id, action, trade_session_id, user_id, entry_price=None, quantity=1):
        """Create a new trade"""
        # Handle UUID string conversion
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                return None
        else:
            user = user_id
            
        trade = cls(
            instrument_id=instrument_id,
            trade_session_id=trade_session_id,
            user_id=user,
            is_active=True,
            started_at=current_ist(),
            view='long' if action == 'buy' else 'short',
            entry_price=entry_price,
            quantity=quantity,
        )
        trade.full_clean()
        trade.save()
        return trade

    @classmethod
    def close_trade(cls, trade_id, exit_price=None, exit_reason=None):
        """Close an active trade"""
        try:
            trade = cls.objects.get(id=trade_id, is_active=True)
            trade.is_active = False
            trade.closed_at = current_ist()
            trade.exit_price = exit_price
            trade.exit_reason = exit_reason
            
            # Calculate net profit if we have both entry and exit prices
            if trade.entry_price and exit_price and trade.quantity:
                if trade.view == 'long':
                    profit_per_unit = Decimal(str(exit_price)) - trade.entry_price
                else:  # short
                    profit_per_unit = trade.entry_price - Decimal(str(exit_price))
                
                trade.net_profit = profit_per_unit * trade.quantity - trade.total_fees
            
            trade.full_clean()
            trade.save()
            return trade
        except cls.DoesNotExist:
            return None

    @classmethod
    def update_trade(cls, trade_id, **kwargs):
        """Update trade with given parameters"""
        try:
            trade = cls.objects.get(id=trade_id)
            for field, value in kwargs.items():
                if hasattr(trade, field):
                    setattr(trade, field, value)
            trade.full_clean()
            trade.save()
            return trade
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_net_profit(cls, trade_id):
        """Calculate net profit for a trade based on orders"""
        try:
            trade = cls.objects.get(id=trade_id)
            if trade.net_profit is not None:
                return float(trade.net_profit)
            
            # Fallback calculation from orders
            orders = trade.order_set.all()
            net_profit = Decimal('0.00')
            for order in orders:
                if order.order_type == 'buy':
                    net_profit -= (order.price * order.quantity)
                elif order.order_type == 'sell':
                    net_profit += (order.price * order.quantity)
                if order.frictional_losses:
                    net_profit -= order.frictional_losses
            
            return float(net_profit)
        except cls.DoesNotExist:
            return 0.0

    @classmethod
    def fetch_active_trades_for_trade_session(cls, trade_session_id):
        """Get all active trades for a trading session"""
        return cls.objects.filter(trade_session_id=trade_session_id, is_active=True)

    @classmethod
    def get_user_trades(cls, user_id, is_active=None, limit=100):
        """Get trades for a user with optional filters"""
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                return cls.objects.none()
        else:
            user = user_id

        queryset = cls.objects.filter(user_id=user)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
            
        return queryset.order_by('-created_at')[:limit]

    @classmethod
    def get_session_trades(cls, trade_session_id, is_active=None):
        """Get all trades for a specific session"""
        queryset = cls.objects.filter(trade_session_id=trade_session_id)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
            
        return queryset.order_by('-created_at')

    def calculate_profit_loss(self):
        """Calculate current profit/loss for the trade"""
        if not self.entry_price or not self.quantity:
            return Decimal('0.00')
        
        if self.exit_price:
            # Trade is closed, use exit price
            current_price = self.exit_price
        else:
            # Trade is open, use current market price
            current_price = self.instrument.last_price
        
        if self.view == 'long':
            profit_per_unit = current_price - self.entry_price
        else:  # short
            profit_per_unit = self.entry_price - current_price
        
        gross_profit = profit_per_unit * self.quantity
        return gross_profit - self.total_fees

    def update_profit_loss(self):
        """Update the net_profit field with current calculation"""
        self.net_profit = self.calculate_profit_loss()
        self.save(update_fields=['net_profit', 'updated_at'])

    @property
    def is_profitable(self):
        """Check if trade is currently profitable"""
        current_pl = self.calculate_profit_loss()
        return current_pl > 0

    @property
    def profit_percentage(self):
        """Calculate profit as percentage of invested amount"""
        if not self.entry_price or not self.quantity:
            return 0.0
        
        invested_amount = self.entry_price * self.quantity
        current_profit = self.calculate_profit_loss()
        
        if invested_amount > 0:
            return float((current_profit / invested_amount) * 100)
        return 0.0

    @property
    def duration(self):
        """Get trade duration"""
        end_time = self.closed_at or timezone.now()
        return end_time - self.started_at

    @property
    def is_stop_loss_hit(self):
        """Check if current price has hit stop loss"""
        if not self.stop_loss_price or not self.instrument.last_price:
            return False
        
        current_price = self.instrument.last_price
        
        if self.view == 'long':
            return current_price <= self.stop_loss_price
        else:  # short
            return current_price >= self.stop_loss_price

    @property
    def is_take_profit_hit(self):
        """Check if current price has hit take profit"""
        if not self.take_profit_price or not self.instrument.last_price:
            return False
        
        current_price = self.instrument.last_price
        
        if self.view == 'long':
            return current_price >= self.take_profit_price
        else:  # short
            return current_price <= self.take_profit_price

    def add_note(self, note):
        """Add a note to the trade"""
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        new_note = f"[{timestamp}] {note}"
        
        if self.trade_notes:
            self.trade_notes = f"{self.trade_notes}\n{new_note}"
        else:
            self.trade_notes = new_note
            
        self.save(update_fields=['trade_notes', 'updated_at'])

    def set_stop_loss(self, price, reason=None):
        """Set stop loss price for the trade"""
        self.stop_loss_price = Decimal(str(price))
        if reason:
            self.add_note(f"Stop loss set at {price}: {reason}")
        else:
            self.add_note(f"Stop loss set at {price}")
        self.save(update_fields=['stop_loss_price', 'updated_at'])

    def set_take_profit(self, price, reason=None):
        """Set take profit price for the trade"""
        self.take_profit_price = Decimal(str(price))
        if reason:
            self.add_note(f"Take profit set at {price}: {reason}")
        else:
            self.add_note(f"Take profit set at {price}")
        self.save(update_fields=['take_profit_price', 'updated_at'])

    @property
    def trade_summary(self):
        """Get a summary of trade information"""
        return {
            'trade_id': self.id,
            'instrument': str(self.instrument),
            'view': self.view,
            'quantity': self.quantity,
            'entry_price': float(self.entry_price) if self.entry_price else None,
            'exit_price': float(self.exit_price) if self.exit_price else None,
            'current_pl': float(self.calculate_profit_loss()),
            'profit_percentage': self.profit_percentage,
            'is_active': self.is_active,
            'duration': str(self.duration),
            'stop_loss': float(self.stop_loss_price) if self.stop_loss_price else None,
            'take_profit': float(self.take_profit_price) if self.take_profit_price else None,
        }



    
