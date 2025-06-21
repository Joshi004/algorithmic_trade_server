from django.db import models
from .ScanningAlgorithm import ScanningAlgorithm
from .InitiationAlgorithm import InitiationAlgorithm
from .TerminationAlgorithm import TerminationAlgorithm
from .Instrument import Instrument


class ScannerEvent(models.Model):
    """
    Model to persist scanner events before publishing to Redis stream.
    Ensures event durability and recovery in case of service failures.
    """
    class Meta:
        db_table = "scanner_events"
        indexes = [
            models.Index(fields=['trade_session_id']),
            models.Index(fields=['event_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['scanning_algorithm_name']),
            models.Index(fields=['instrument']),
        ]

    id = models.BigAutoField(primary_key=True)
    event_id = models.CharField(max_length=100, unique=True, db_index=True)
    event_type = models.CharField(max_length=50, default='eligible_instrument_found')
    trade_session_id = models.CharField(max_length=100, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    
    # Foreign key to instrument
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    trading_symbol = models.CharField(max_length=200, db_index=True)
    
    # Price fields
    support_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    resistance_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    required_action = models.CharField(max_length=10, null=True, blank=True)  # 'buy', 'sell', or null
    market_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Algorithm foreign keys based on names for data integrity
    scanning_algorithm_name = models.ForeignKey(ScanningAlgorithm, to_field='name', on_delete=models.CASCADE)
    initiation_algorithm_name = models.ForeignKey(InitiationAlgorithm, to_field='name', on_delete=models.CASCADE)
    termination_algorithm_name = models.ForeignKey(TerminationAlgorithm, to_field='name', on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ScannerEvent {self.event_id} - {self.trading_symbol} ({self.event_type})"

    @classmethod
    def create_event(cls, event_data):
        """
        Create a new scanner event record.
        
        Args:
            event_data: Dictionary containing event details
            
        Returns:
            ScannerEvent: Created event instance
        """
        return cls.objects.create(**event_data) 