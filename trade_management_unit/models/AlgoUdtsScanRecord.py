from django.db import models
from enum import Enum
from decimal import Decimal, ROUND_DOWN
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from trade_management_unit.models.Trade import Trade
from trade_management_unit.models.Instrument import Instrument  # Import the Instrument model
from trade_management_unit.models.Algorithm import Algorithm  # Import the Algorithm model
from trade_management_unit.Constants.TmuConstants import *

class AlgoUdtsScanRecord(models.Model):
    class Meta:
        db_table = "algo_udts_scan_records"
        unique_together = (('trade', 'instrument'),)

    id = models.AutoField(primary_key=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    market_price = models.DecimalField(max_digits=10, decimal_places=2)
    support_price = models.DecimalField(max_digits=10, decimal_places=2)
    resistance_price = models.DecimalField(max_digits=10, decimal_places=2)
    support_strength = models.DecimalField(max_digits=10, decimal_places=4)
    resistance_strength = models.DecimalField(max_digits=10, decimal_places=4)
    effective_trend = models.CharField(max_length=20,choices=Trends.choices(),default=Trends.UPTREND,)
    trade_candle_interval = models.CharField(max_length=255)
    movement_potential = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.DecimalField(max_digits=20, decimal_places=2)
    trade = models.ForeignKey('Trade', on_delete=models.CASCADE)
    instrument = models.ForeignKey('Instrument', on_delete=models.PROTECT)
    tracking_algo = models.ForeignKey('Algorithm', on_delete=models.PROTECT)

    @classmethod
    def fetch_udts_record(cls,trade_id):
        udts_record = cls.objects.get(
            trade_id = trade_id,
        )
        return udts_record

    @classmethod
    def add_entry(cls, *, market_price, support_price, resistance_price, support_strength, resistance_strength, effective_trend, trade_candle_interval, movement_potential, trade_id, instrument_id, tracking_algo_name,volume):  # Add instrument_id parameter
        # Get the Trade instance
        try:
            trade = Trade.objects.get(pk=trade_id)
        except ObjectDoesNotExist:
            raise ValidationError(f"Trade with id {trade_id} does not exist.")

        # Get the Instrument instance
        try:
            instrument = Instrument.objects.get(pk=instrument_id)  # Get the Instrument instance using instrument_id
        except ObjectDoesNotExist:
            raise ValidationError(f"Instrument with id {instrument_id} does not exist.")

        # try:
        #     udts_record = cls.fetch_udts_record(trade_id)
        #     return udts_record
        # except:
        # Round off the values to the desired format
        market_price = Decimal(market_price).quantize(Decimal('.01'), rounding=ROUND_DOWN)
        support_price = Decimal(support_price).quantize(Decimal('.01'), rounding=ROUND_DOWN)
        resistance_price = Decimal(resistance_price).quantize(Decimal('.01'), rounding=ROUND_DOWN)
        support_strength = Decimal(support_strength).quantize(Decimal('.0001'), rounding=ROUND_DOWN)
        resistance_strength = Decimal(resistance_strength).quantize(Decimal('.0001'), rounding=ROUND_DOWN)
        movement_potential = Decimal(movement_potential).quantize(Decimal('.01'), rounding=ROUND_DOWN)
        volume = Decimal(volume).quantize(Decimal('.01'), rounding=ROUND_DOWN)

        # Validate the trend value
        if effective_trend not in Trends._value2member_map_:
            raise ValidationError(f"Invalid trend value: {effective_trend}. Expected one of: {', '.join(Trends._value2member_map_.keys())}")

         # Get the Algorithm instance
        try:
            tracking_algo = Algorithm.objects.get(name=tracking_algo_name)  # Get the Algorithm instance using tracking_algo_name
        except ObjectDoesNotExist:
            raise ValidationError(f"Algorithm with name {tracking_algo_name} does not exist.")

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
            volume=volume,
            trade=trade,
            instrument=instrument,
            tracking_algo=tracking_algo
        )
        record.full_clean()
        record.save()
        return record
