from django.db import models
from enum import Enum
from decimal import Decimal, ROUND_DOWN
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from trade_management_unit.models.Trade import Trade
from trade_management_unit.Constants.TmuConstants import *

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
    resistance_price = models.DecimalField(max_digits=10, decimal_places=2)
    support_strength = models.DecimalField(max_digits=10, decimal_places=4)
    resistance_strength = models.DecimalField(max_digits=10, decimal_places=4)
    TREND_CHOICES = [(trend, trend) for trend in Trends]
    effective_trend = models.CharField(
        max_length=20,
        choices=Trends.choices(),
        default=Trends.UPTREND,
    )
    trade_candle_interval = models.CharField(max_length=255)
    movement_potential = models.DecimalField(max_digits=10, decimal_places=2)
    trade = models.ForeignKey('Trade', on_delete=models.CASCADE)

    @classmethod
    def add_entry(cls, *, market_price, support_price, resistance_price, support_strength, resistance_strength, effective_trend, trade_candle_interval, movement_potential, trade_id):
        # Round off the values to the desired format
        market_price = Decimal(market_price).quantize(Decimal('.01'), rounding=ROUND_DOWN)
        support_price = Decimal(support_price).quantize(Decimal('.01'), rounding=ROUND_DOWN)
        resistance_price = Decimal(resistance_price).quantize(Decimal('.01'), rounding=ROUND_DOWN)
        support_strength = Decimal(support_strength).quantize(Decimal('.0001'), rounding=ROUND_DOWN)
        resistance_strength = Decimal(resistance_strength).quantize(Decimal('.0001'), rounding=ROUND_DOWN)
        movement_potential = Decimal(movement_potential).quantize(Decimal('.01'), rounding=ROUND_DOWN)

        # Validate the trend value
        if effective_trend not in Trends._value2member_map_:
            raise ValidationError(f"Invalid trend value: {effective_trend}. Expected one of: {', '.join(Trends._value2member_map_.keys())}")

        # Get the Trade instance
        try:
            trade = Trade.objects.get(pk=trade_id)
        except ObjectDoesNotExist:
            raise ValidationError(f"Trade with id {trade_id} does not exist.")

        # Create and save the new record
        record = cls(
            market_price=market_price,
            support_price=support_price,
            resistance_price=resistance_price,
            support_strength=support_strength,
            resistance_strength=resistance_strength,
            effective_trend=effective_trend,
            trade_candle_interval=trade_candle_interval,
            movement_potential=movement_potential,
            trade=trade
        )
        
        record.full_clean()  # This will validate all fields and raise a ValidationError if any field is invalid
        record.save()

        return record
