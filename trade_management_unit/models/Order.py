from django.db import models
from django_mysql.models import EnumField
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from ats_gateway.models.User import User
from decimal import Decimal
from trade_management_unit.lib.common.Utils.Utils import current_ist
from trade_management_unit.lib.common.Utils.custome_logger import log


class Order(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False)
    
    # User reference - ForeignKey to User.public_id
    user_id = models.ForeignKey(
        User,
        to_field='public_id',
        on_delete=models.CASCADE,
        db_column='user_id',
        help_text='References User.public_id'
    )
    
    # Order status and type
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("executed", "Executed"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
        ("partially_filled", "Partially Filled")
    ]
    status = EnumField(
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
        help_text='Current status of the order'
    )
    
    ORDER_TYPES = [("buy", "Buy"), ("sell", "Sell")]
    order_type = EnumField(
        choices=ORDER_TYPES,
        db_index=True,
        help_text='Order type: buy or sell'
    )
    
    # Order timing
    started_at = models.DateTimeField(
        default=timezone.now,
        help_text='When the order was placed'
    )
    closed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When the order was executed/closed'
    )
    
    # Order relationships
    instrument = models.ForeignKey(
        "Instrument",
        on_delete=models.PROTECT,
        verbose_name="instrument_id",
        help_text='The financial instrument for this order'
    )
    trade = models.ForeignKey(
        "Trade",
        on_delete=models.CASCADE,
        verbose_name="trade_id",
        help_text='The parent trade for this order'
    )
    trade_session = models.ForeignKey(
        "TradeSession",
        on_delete=models.CASCADE,
        verbose_name="trade_session_id",
        help_text='The trading session this order belongs to'
    )
    
    # Order details
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Number of units in this order'
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Order price per unit'
    )
    filled_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of units that have been filled'
    )
    average_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Average execution price'
    )
    
    # Broker integration
    kite_order_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text='Broker order ID for tracking'
    )
    broker_order_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text='Generic broker order ID'
    )
    
    # Order execution details
    frictional_losses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Fees, taxes, and other charges'
    )
    total_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total value of the order'
    )
    
    # Order metadata
    order_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Notes or comments about this order'
    )
    rejection_reason = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Reason for order rejection'
    )
    order_source = models.CharField(
        max_length=50,
        default='system',
        help_text='Source of the order: system, manual, etc.'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']
        unique_together = (('trade', 'order_type'),)
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['status']),
            models.Index(fields=['order_type']),
            models.Index(fields=['started_at']),
            models.Index(fields=['closed_at']),
            models.Index(fields=['kite_order_id']),
            models.Index(fields=['broker_order_id']),
            models.Index(fields=['instrument']),
            models.Index(fields=['trade']),
            models.Index(fields=['trade_session']),
            # Composite indexes
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['user_id', 'trade']),
            models.Index(fields=['trade', 'order_type']),
            models.Index(fields=['trade_session', 'status']),
            models.Index(fields=['status', 'started_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(closed_at__isnull=True) | models.Q(closed_at__gte=models.F('started_at')),
                name='chk_orders_date_order'
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gt=0) & models.Q(filled_quantity__gte=0) & models.Q(filled_quantity__lte=models.F('quantity')),
                name='chk_orders_positive_quantity'
            ),
        ]

    def __str__(self):
        return f"Order {self.id} - {self.order_type} {self.quantity} {self.instrument.trading_symbol} ({self.status})"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate that closed_at >= started_at
        if self.closed_at and self.started_at and self.closed_at < self.started_at:
            raise ValidationError({'closed_at': 'Order close time cannot be before start time'})
        
        # Validate filled quantity
        if self.filled_quantity > self.quantity:
            raise ValidationError({'filled_quantity': 'Filled quantity cannot exceed order quantity'})

    @classmethod
    def initiate_order(cls, order_type, instrument_id, trade_id, user_id, quantity=1, price=None, trade_session_id=None, broker_order_id=None):
        """Create a new order or return existing one"""
        # Handle UUID string conversion
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                return None
        else:
            user = user_id

        with transaction.atomic():
            existing_order = cls.objects.select_for_update().filter(
                trade_id=trade_id, 
                order_type=order_type
            ).first()
            
            if existing_order:
                return existing_order

            # Get trade_session_id from trade if not provided
            if not trade_session_id:
                from trade_management_unit.models.Trade import Trade
                try:
                    trade = Trade.objects.get(id=trade_id)
                    trade_session_id = trade.trade_session_id
                except Trade.DoesNotExist:
                    log(f'Trade with id {trade_id} does not exist', 'error')
                    return None

            order = cls(
                status='pending',
                order_type=order_type,
                started_at=current_ist(),
                instrument_id=instrument_id,
                trade_id=trade_id,
                user_id=user,
                quantity=quantity,
                price=price,
                trade_session_id=trade_session_id,
                broker_order_id=broker_order_id,
                total_value=price * quantity if price else Decimal('0.00')
            )
            order.full_clean()
            order.save()
            return order

    @classmethod
    def execute_order(cls, order_id, execution_price=None, execution_quantity=None, frictional_losses=None):
        """Mark an order as executed"""
        try:
            order = cls.objects.get(id=order_id)
            
            if order.status != 'pending':
                raise ValidationError(f"Cannot execute order with status: {order.status}")
            
            execution_quantity = execution_quantity or order.quantity
            execution_price = execution_price or order.price
            
            if not execution_price:
                raise ValidationError("Execution price is required")
            
            order.status = 'executed' if execution_quantity == order.quantity else 'partially_filled'
            order.filled_quantity = execution_quantity
            order.average_price = execution_price
            order.closed_at = current_ist()
            order.total_value = execution_price * execution_quantity
            
            if frictional_losses:
                order.frictional_losses = Decimal(str(frictional_losses))
                order.total_value += order.frictional_losses
            
            order.full_clean()
            order.save()
            return order
            
        except cls.DoesNotExist:
            log(f'Order with id {order_id} does not exist', 'error')
            return None

    @classmethod
    def reject_order(cls, order_id, rejection_reason=None):
        """Mark an order as rejected"""
        try:
            order = cls.objects.get(id=order_id)
            
            if order.status != 'pending':
                raise ValidationError(f"Cannot reject order with status: {order.status}")
            
            order.status = 'rejected'
            order.rejection_reason = rejection_reason
            order.closed_at = current_ist()
            order.full_clean()
            order.save()
            return order
            
        except cls.DoesNotExist:
            log(f'Order with id {order_id} does not exist', 'error')
            return None

    @classmethod
    def cancel_order(cls, order_id, cancellation_reason=None):
        """Cancel a pending order"""
        try:
            order = cls.objects.get(id=order_id)
            
            if order.status not in ['pending', 'partially_filled']:
                raise ValidationError(f"Cannot cancel order with status: {order.status}")
            
            order.status = 'cancelled'
            order.closed_at = current_ist()
            if cancellation_reason:
                order.add_note(f"Cancelled: {cancellation_reason}")
            order.full_clean()
            order.save()
            return order
            
        except cls.DoesNotExist:
            log(f'Order with id {order_id} does not exist', 'error')
            return None

    @classmethod
    def fetch_order(cls, trade_id: int):
        """Fetch order by trade ID"""
        if not cls.objects.filter(trade_id=trade_id).exists():
            raise ValidationError(f"No trade found with id {trade_id}.")

        try:
            return cls.objects.get(trade_id=trade_id)
        except cls.MultipleObjectsReturned:
            log(f'Multiple orders found for trade {trade_id}', 'error')
            return cls.objects.filter(trade_id=trade_id).first()
        except cls.DoesNotExist:
            raise ValidationError("No matching order found.")

    @classmethod
    def get_user_orders(cls, user_id, status=None, order_type=None, limit=100):
        """Get orders for a user with optional filters"""
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                return cls.objects.none()
        else:
            user = user_id

        queryset = cls.objects.filter(user_id=user)
        
        if status:
            queryset = queryset.filter(status=status)
        if order_type:
            queryset = queryset.filter(order_type=order_type)
            
        return queryset.order_by('-created_at')[:limit]

    @classmethod
    def get_trade_orders(cls, trade_id, status=None):
        """Get all orders for a specific trade"""
        queryset = cls.objects.filter(trade_id=trade_id)
        
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-created_at')

    @classmethod
    def get_session_orders(cls, trade_session_id, status=None):
        """Get all orders for a specific session"""
        queryset = cls.objects.filter(trade_session_id=trade_session_id)
        
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-created_at')

    @classmethod
    def get_pending_orders(cls, user_id=None):
        """Get all pending orders, optionally filtered by user"""
        queryset = cls.objects.filter(status='pending')
        
        if user_id:
            if isinstance(user_id, str):
                try:
                    user = User.objects.get(public_id=user_id)
                    queryset = queryset.filter(user_id=user)
                except User.DoesNotExist:
                    return cls.objects.none()
            else:
                queryset = queryset.filter(user_id=user_id)
                
        return queryset.order_by('-created_at')

    def calculate_execution_value(self):
        """Calculate the total execution value including fees"""
        if self.average_price and self.filled_quantity:
            base_value = self.average_price * self.filled_quantity
            return base_value + (self.frictional_losses or Decimal('0.00'))
        return Decimal('0.00')

    def update_broker_status(self, broker_order_id, status, execution_price=None, execution_quantity=None):
        """Update order status based on broker feedback"""
        self.broker_order_id = broker_order_id
        
        if status == 'COMPLETE':
            if execution_price and execution_quantity:
                return self.execute_order(self.id, execution_price, execution_quantity)
        elif status == 'REJECTED':
            return self.reject_order(self.id, "Rejected by broker")
        elif status == 'CANCELLED':
            return self.cancel_order(self.id, "Cancelled by broker")
        
        # For other statuses, just update the order
        self.save(update_fields=['broker_order_id', 'updated_at'])
        return self

    @property
    def is_pending(self):
        """Check if order is pending"""
        return self.status == 'pending'

    @property
    def is_executed(self):
        """Check if order is fully executed"""
        return self.status == 'executed'

    @property
    def is_partially_filled(self):
        """Check if order is partially filled"""
        return self.status == 'partially_filled'

    @property
    def remaining_quantity(self):
        """Get remaining unfilled quantity"""
        return self.quantity - self.filled_quantity

    @property
    def fill_percentage(self):
        """Get fill percentage"""
        if self.quantity > 0:
            return (self.filled_quantity / self.quantity) * 100
        return 0.0

    @property
    def duration(self):
        """Get order duration"""
        end_time = self.closed_at or timezone.now()
        return end_time - self.started_at

    def add_note(self, note):
        """Add a note to the order"""
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        new_note = f"[{timestamp}] {note}"
        
        if self.order_notes:
            self.order_notes = f"{self.order_notes}\n{new_note}"
        else:
            self.order_notes = new_note
            
        self.save(update_fields=['order_notes', 'updated_at'])

    @property
    def order_summary(self):
        """Get a summary of order information"""
        return {
            'order_id': self.id,
            'order_type': self.order_type,
            'status': self.status,
            'instrument': str(self.instrument),
            'quantity': self.quantity,
            'filled_quantity': self.filled_quantity,
            'remaining_quantity': self.remaining_quantity,
            'price': float(self.price) if self.price else None,
            'average_price': float(self.average_price) if self.average_price else None,
            'total_value': float(self.total_value),
            'frictional_losses': float(self.frictional_losses) if self.frictional_losses else None,
            'fill_percentage': self.fill_percentage,
            'duration': str(self.duration),
            'broker_order_id': self.broker_order_id,
        }
