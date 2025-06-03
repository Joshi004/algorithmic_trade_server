from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


class Instrument(models.Model):    
    # Use BigIntegerField for instrument ID (from broker)
    id = models.BigIntegerField(primary_key=True, help_text='Broker-provided instrument ID')
    
    # Broker-specific identifiers
    instrument_token = models.BigIntegerField(unique=True, db_index=True, help_text='Unique instrument token from broker')
    exchange_token = models.BigIntegerField(db_index=True, help_text='Exchange-specific token')
    
    # Basic instrument information
    trading_symbol = models.CharField(max_length=200, db_index=True, help_text='Trading symbol (e.g., RELIANCE)')
    name = models.CharField(max_length=200, db_index=True, help_text='Full instrument name')
    
    # Price and trading information
    last_price = models.DecimalField(max_digits=12, decimal_places=2, help_text='Last traded price')
    tick_size = models.DecimalField(max_digits=10, decimal_places=4, help_text='Minimum price movement')
    lot_size = models.IntegerField(validators=[MinValueValidator(1)], help_text='Trading lot size')
    
    # Options/Futures specific fields
    expiry = models.DateField(null=True, blank=True, help_text='Expiry date for derivatives')
    strike = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text='Strike price for options')
    
    # Classification fields
    instrument_type = models.CharField(max_length=50, db_index=True, help_text='Type: EQ, FUT, CE, PE, etc.')
    segment = models.CharField(max_length=50, db_index=True, help_text='Market segment')
    exchange = models.CharField(max_length=50, db_index=True, help_text='Exchange: NSE, BSE, etc.')
    
    # Status and metadata
    is_active = models.BooleanField(default=True, db_index=True, help_text='Whether instrument is currently tradeable')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "instruments"
        verbose_name = "Instrument"
        verbose_name_plural = "Instruments"
        ordering = ['trading_symbol']
        indexes = [
            # Composite indexes for common query patterns
            models.Index(fields=['trading_symbol', 'exchange'], name='idx_instruments_symbol_exchange'),
            models.Index(fields=['instrument_type', 'segment'], name='idx_instruments_type_segment'),
            models.Index(fields=['exchange', 'is_active'], name='idx_instruments_exchange_active'),
            models.Index(fields=['expiry'], name='idx_instruments_expiry'),
            models.Index(fields=['is_active', 'instrument_type'], name='idx_instruments_active_type'),
        ]

    def __str__(self):
        return f"{self.trading_symbol} ({self.exchange})"

    @classmethod
    def get_active_instruments(cls, exchange=None, instrument_type=None):
        """Get all active instruments, optionally filtered by exchange and type"""
        queryset = cls.objects.filter(is_active=True)
        if exchange:
            queryset = queryset.filter(exchange=exchange)
        if instrument_type:
            queryset = queryset.filter(instrument_type=instrument_type)
        return queryset

    @classmethod
    def get_by_symbol_and_exchange(cls, trading_symbol, exchange):
        """Get instrument by trading symbol and exchange"""
        try:
            return cls.objects.get(trading_symbol=trading_symbol, exchange=exchange, is_active=True)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_instrument_token(cls, instrument_token):
        """Get instrument by instrument token"""
        try:
            return cls.objects.get(instrument_token=instrument_token, is_active=True)
        except cls.DoesNotExist:
            return None

    @property
    def is_derivative(self):
        """Check if instrument is a derivative (futures/options)"""
        return self.instrument_type in ['FUT', 'CE', 'PE']

    @property
    def is_equity(self):
        """Check if instrument is equity"""
        return self.instrument_type == 'EQ'

    @property
    def is_option(self):
        """Check if instrument is an option"""
        return self.instrument_type in ['CE', 'PE']

    @property
    def is_future(self):
        """Check if instrument is a future"""
        return self.instrument_type == 'FUT'

    @property
    def display_name(self):
        """Get display-friendly name"""
        if self.is_option and self.strike:
            return f"{self.trading_symbol} {self.strike} {self.instrument_type}"
        return self.trading_symbol

    def update_last_price(self, new_price):
        """Update the last price and save"""
        if isinstance(new_price, (int, float, Decimal)):
            self.last_price = Decimal(str(new_price))
            self.save(update_fields=['last_price', 'updated_at'])
            return True
        return False

    def calculate_trade_value(self, quantity=1):
        """Calculate total trade value for given quantity"""
        return self.last_price * quantity * self.lot_size

    @classmethod
    def search_instruments(cls, query, limit=50):
        """Search instruments by name or trading symbol"""
        return cls.objects.filter(
            models.Q(trading_symbol__icontains=query) | models.Q(name__icontains=query),
            is_active=True
        )[:limit]
