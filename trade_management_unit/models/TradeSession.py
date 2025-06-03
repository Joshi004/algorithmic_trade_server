from django.db import models
from django_mysql.models import EnumField
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from ats_gateway.models.User import User
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm
from trade_management_unit.Constants.TmuConstants import FREQUENCY
from trade_management_unit.lib.common.Utils.Utils import current_ist
from decimal import Decimal
import uuid


class TradeSession(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False)
    
    # User reference - ForeignKey to User.public_id
    user_id = models.ForeignKey(
        User,
        to_field='public_id',
        on_delete=models.CASCADE,
        db_column='user_id',
        help_text='References User.public_id'
    )
    
    # Session status with enhanced choices
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('paused', 'Paused'),
        ('stopped', 'Stopped'),
        ('completed', 'Completed'),
        ('error', 'Error'),
        ('terminated', 'Terminated')
    ]
    status = EnumField(
        choices=STATUS_CHOICES,
        default='started',
        db_index=True,
        help_text='Current status of the trading session'
    )
    
    # Algorithm references with proper foreign keys
    scanning_algorithm = models.ForeignKey(
        ScanningAlgorithm,
        on_delete=models.PROTECT,
        help_text='Scanning algorithm for this session'
    )
    initiation_algorithm = models.ForeignKey(
        InitiationAlgorithm,
        on_delete=models.PROTECT,
        help_text='Trade initiation algorithm for this session'
    )
    termination_algorithm = models.ForeignKey(
        TerminationAlgorithm,
        on_delete=models.PROTECT,
        help_text='Trade termination algorithm for this session'
    )
    
    # Trading configuration
    TRADING_FREQUENCY_CHOICES = [(freq, freq) for freq in FREQUENCY]
    trading_frequency = EnumField(
        choices=TRADING_FREQUENCY_CHOICES,
        default='10minute',
        db_index=True,
        help_text='Trading frequency for this session'
    )
    
    # Session timing
    started_at = models.DateTimeField(
        blank=False,
        help_text='When the session was started'
    )
    closed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When the session was closed'
    )
    
    # Session flags
    dummy = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this is a paper trading session'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether the session is currently active'
    )
    
    # Performance tracking
    total_trades = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total number of trades in this session'
    )
    successful_trades = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of profitable trades'
    )
    net_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Net profit/loss for this session'
    )
    total_volume = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total trading volume in this session'
    )
    
    # Risk management
    max_drawdown = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Maximum drawdown during the session'
    )
    current_exposure = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Current market exposure'
    )
    
    # Session metadata
    session_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Notes or comments about this session'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text='Error message if session encountered an error'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trade_sessions"
        verbose_name = "Trade Session"
        verbose_name_plural = "Trade Sessions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['status']),
            models.Index(fields=['dummy']),
            models.Index(fields=['is_active']),
            models.Index(fields=['trading_frequency']),
            models.Index(fields=['started_at']),
            models.Index(fields=['scanning_algorithm']),
            models.Index(fields=['initiation_algorithm']),
            models.Index(fields=['termination_algorithm']),
            # Composite indexes
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['user_id', 'dummy']),
            models.Index(fields=['user_id', 'is_active']),
            models.Index(fields=['is_active', 'trading_frequency']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(closed_at__isnull=True) | models.Q(closed_at__gte=models.F('started_at')),
                name='chk_trade_sessions_date_order'
            ),
            models.CheckConstraint(
                check=models.Q(successful_trades__lte=models.F('total_trades')),
                name='chk_trade_sessions_positive_trades'
            ),
        ]

    def __str__(self):
        return f"Session {self.id} - {self.user_id} ({self.status})"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate that successful_trades <= total_trades
        if self.successful_trades > self.total_trades:
            raise ValidationError({'successful_trades': 'Successful trades cannot exceed total trades'})
        
        # Validate session dates
        if self.closed_at and self.started_at and self.closed_at < self.started_at:
            raise ValidationError({'closed_at': 'Session close time cannot be before start time'})

    @classmethod
    def fetch_or_create_trade_session(cls, scanning_algo_id, initiation_algo_id, termination_algo_id, trading_freq, is_dummy, user_id):
        """
        Fetch existing session or create new one with given parameters
        """
        # Validate that the algorithm IDs exist
        try:
            ScanningAlgorithm.objects.get(id=scanning_algo_id, is_active=True)
            InitiationAlgorithm.objects.get(id=initiation_algo_id, is_active=True)
            TerminationAlgorithm.objects.get(id=termination_algo_id, is_active=True)
        except (ScanningAlgorithm.DoesNotExist, InitiationAlgorithm.DoesNotExist, TerminationAlgorithm.DoesNotExist):
            return None, "One or more algorithm IDs are invalid or inactive"

        # Handle UUID string conversion
        if isinstance(user_id, str):
            try:
                user = User.objects.get(public_id=user_id)
            except User.DoesNotExist:
                return None, f"User with public_id {user_id} does not exist"
        else:
            user = user_id

        with transaction.atomic():
            try:
                trade_session = cls.objects.get(
                    user_id=user,
                    scanning_algorithm_id=scanning_algo_id,
                    initiation_algorithm_id=initiation_algo_id,
                    termination_algorithm_id=termination_algo_id,
                    trading_frequency=trading_freq,
                    dummy=is_dummy,
                    status__in=['started', 'paused']  # Only active sessions
                )
                return trade_session, "Session already exists"
            except cls.DoesNotExist:
                # Create new session
                trade_session = cls(
                    user_id=user,
                    scanning_algorithm_id=scanning_algo_id,
                    initiation_algorithm_id=initiation_algo_id,
                    termination_algorithm_id=termination_algo_id,
                    trading_frequency=trading_freq,
                    status='started',
                    started_at=current_ist(),
                    dummy=is_dummy
                )
                trade_session.full_clean()
                trade_session.save()
                
                # Publish event to Redis stream for new session creation
                try:
                    from trade_management_unit.lib.common.event_publisher import get_trade_session_event_publisher
                    event_publisher = get_trade_session_event_publisher()
                    event_publisher.publish_trade_session_initiated(trade_session, "New session created")
                except Exception as e:
                    from trade_management_unit.lib.common.Utils.custome_logger import log
                    log(f"Failed to publish trade session initiation event for session {trade_session.id}: {str(e)}", level="error")
                
                return trade_session, "New session created"

    @classmethod
    def fetch_active_trade_session(cls, user_id, scanning_algo_id, initiation_algo_id, termination_algo_id, trading_freq, is_dummy):
        """
        Fetch an active trade session with the given parameters
        """
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
                user_id=user,
                scanning_algorithm_id=scanning_algo_id,
                initiation_algorithm_id=initiation_algo_id,
                termination_algorithm_id=termination_algo_id,
                trading_frequency=trading_freq,
                dummy=is_dummy,
                status='started',
                is_active=True
            )
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_user_sessions(cls, user_id, status=None, dummy=None, limit=50):
        """
        Get sessions for a user with optional filters
        """
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
        if dummy is not None:
            queryset = queryset.filter(dummy=dummy)
            
        return queryset.order_by('-created_at')[:limit]

    @classmethod
    def get_active_sessions(cls, user_id=None):
        """
        Get all active sessions, optionally filtered by user
        """
        queryset = cls.objects.filter(is_active=True, status__in=['started', 'paused'])
        
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

    def pause_session(self, reason=None):
        """
        Pause the trading session
        """
        if self.status != 'started':
            raise ValidationError("Can only pause started sessions")
            
        self.status = 'paused'
        if reason:
            self.session_notes = f"{self.session_notes or ''}\nPaused: {reason}".strip()
        self.save(update_fields=['status', 'session_notes', 'updated_at'])

    def resume_session(self):
        """
        Resume a paused trading session
        """
        if self.status != 'paused':
            raise ValidationError("Can only resume paused sessions")
            
        self.status = 'started'
        self.session_notes = f"{self.session_notes or ''}\nResumed at {timezone.now()}".strip()
        self.save(update_fields=['status', 'session_notes', 'updated_at'])

    def stop_session(self, reason=None):
        """
        Stop the trading session
        """
        if self.status in ['stopped', 'completed', 'terminated']:
            raise ValidationError("Session is already stopped")
            
        self.status = 'stopped'
        self.closed_at = timezone.now()
        self.is_active = False
        
        if reason:
            self.session_notes = f"{self.session_notes or ''}\nStopped: {reason}".strip()
            
        self.save(update_fields=['status', 'closed_at', 'is_active', 'session_notes', 'updated_at'])

        # Publish termination event
        try:
            from trade_management_unit.lib.common.event_publisher import get_trade_session_event_publisher
            event_publisher = get_trade_session_event_publisher()
            event_publisher.publish_trade_session_terminated(self, reason or "Session stopped")
        except Exception as e:
            from trade_management_unit.lib.common.Utils.custome_logger import log
            log(f"Failed to publish trade session termination event for session {self.id}: {str(e)}", level="error")

    def update_performance(self, trade_count_delta=0, successful_trade_delta=0, profit_delta=0, volume_delta=0):
        """
        Update session performance metrics
        """
        self.total_trades += trade_count_delta
        self.successful_trades += successful_trade_delta
        self.net_profit += Decimal(str(profit_delta))
        self.total_volume += Decimal(str(volume_delta))
        
        # Update max drawdown if we have a loss
        if profit_delta < 0:
            current_drawdown = abs(profit_delta)
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
        
        self.save(update_fields=['total_trades', 'successful_trades', 'net_profit', 'total_volume', 'max_drawdown', 'updated_at'])

    def update_exposure(self, new_exposure):
        """
        Update current market exposure
        """
        self.current_exposure = Decimal(str(new_exposure))
        self.save(update_fields=['current_exposure', 'updated_at'])

    @property
    def duration(self):
        """
        Get session duration
        """
        end_time = self.closed_at or timezone.now()
        return end_time - self.started_at

    @property
    def success_rate(self):
        """
        Calculate success rate as percentage
        """
        if self.total_trades == 0:
            return 0
        return (self.successful_trades / self.total_trades) * 100

    @property
    def average_profit_per_trade(self):
        """
        Calculate average profit per trade
        """
        if self.total_trades == 0:
            return Decimal('0.00')
        return self.net_profit / self.total_trades

    @property
    def is_profitable(self):
        """
        Check if session is profitable
        """
        return self.net_profit > 0

    @property
    def session_summary(self):
        """
        Get a summary of session performance
        """
        return {
            'session_id': self.id,
            'status': self.status,
            'duration': str(self.duration),
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'success_rate': f"{self.success_rate:.2f}%",
            'net_profit': float(self.net_profit),
            'total_volume': float(self.total_volume),
            'max_drawdown': float(self.max_drawdown),
            'current_exposure': float(self.current_exposure),
            'is_profitable': self.is_profitable,
        }

    def add_note(self, note):
        """
        Add a note to the session
        """
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        new_note = f"[{timestamp}] {note}"
        
        if self.session_notes:
            self.session_notes = f"{self.session_notes}\n{new_note}"
        else:
            self.session_notes = new_note
            
        self.save(update_fields=['session_notes', 'updated_at'])

    def set_error(self, error_message):
        """
        Set session to error state with message
        """
        self.status = 'error'
        self.error_message = error_message
        self.is_active = False
        self.save(update_fields=['status', 'error_message', 'is_active', 'updated_at'])




