from django.db import models
from django_mysql.models import EnumField
from trade_management_unit.models.Algorithm import Algorithm
from trade_management_unit.models.Algorithm import AlgorithmType
from trade_management_unit.Constants.TmuConstants import FREQUENCY  # assuming constants.py is in the same directory

class TradeSession(models.Model):
    class Meta:
        db_table = "trade_sessions"
  
    id = models.CharField(auto_created=True, primary_key=True, blank=False, max_length=64,) 
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(blank=False)
    closed_at = models.DateTimeField(blank=True, null=True)
    scanning_algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, limit_choices_to={'type': AlgorithmType.SCANNING.value}, related_name='scanning_sessions',default=1)
    tracking_algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, limit_choices_to={'type': AlgorithmType.TRACKING.value}, related_name='tracking_sessions',default=1)
    user_id = models.CharField(max_length=64, blank=False, default="1")
    dummy = models.BooleanField(default=False)

    TRADING_FREQUENCY_CHOICES = [(freq, freq) for freq in FREQUENCY]
    trading_frequency = EnumField(choices=TRADING_FREQUENCY_CHOICES, default="10minute")