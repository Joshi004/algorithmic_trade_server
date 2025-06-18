from django.db import models
from django.utils import timezone


class ScannerInstance(models.Model):
    """
    Model to track active scanner instances across containers.
    This serves as a fallback mechanism in case of Redis failure.
    """
    
    # Auto-generated primary key
    id = models.AutoField(primary_key=True)
    
    # Foreign key to scanning algorithm
    algorithm = models.ForeignKey(
        'trade_management_unit.ScanningAlgorithm',
        on_delete=models.CASCADE,
        related_name='scanner_instances'
    )
    
    # Trading frequency (e.g., '5min', '15min', etc.)
    frequency = models.CharField(max_length=10)
    
    # Whether this scanner instance is currently active
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scanner_instances'
        # Ensure unique combination of algorithm and frequency when active
        constraints = [
            models.UniqueConstraint(
                fields=['algorithm', 'frequency'],
                condition=models.Q(is_active=True),
                name='unique_active_scanner_per_algo_freq'
            )
        ]
        indexes = [
            models.Index(fields=['algorithm', 'frequency', 'is_active']),
        ]
    
    def __str__(self):
        return f"Scanner: {self.algorithm.name} - {self.frequency} ({'Active' if self.is_active else 'Inactive'})" 