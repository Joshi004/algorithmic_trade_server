from django.db import models
from enum import Enum

class Trend(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

class AlgoUdtsScanRecord(models.Model):
    class Meta:
        db_table = "algo_udts_scan_records"
  
    id = models.AutoField(primary_key=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    market_price = models.DecimalField(max_digits=10, decimal_places=2)
    support_price = models.DecimalField(max_digits=10, decimal_places=2)
    resistence_price = models.DecimalField(max_digits=10, decimal_places=2)
    support_strength = models.DecimalField(max_digits=10, decimal_places=4)
    resistence_strength = models.DecimalField(max_digits=10, decimal_places=4)
    effective_trend = models.CharField(
        max_length=20,
        choices=Trend.choices(),
        default=Trend.BULLISH.value,
    )
    trade_candle_interval = models.CharField(max_length=255)
    movement_potential = models.DecimalField(max_digits=10, decimal_places=2)
    trade = models.ForeignKey('Trade', on_delete=models.CASCADE)

