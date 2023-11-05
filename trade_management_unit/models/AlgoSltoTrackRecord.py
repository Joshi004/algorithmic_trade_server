from django.db import models
from django_mysql.models import EnumField
from trade_management_unit.Constants.TmuConstants import PriceZone  # assuming constants.py is in the same directory
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from trade_management_unit.models.Instrument import Instrument
from trade_management_unit.models.Trade import Trade
from trade_management_unit.models.Algorithm import Algorithm
from datetime import datetime
class AlgoSltoTrackRecord(models.Model):
    class Meta:
        db_table = "algo_slto_track_records"
        unique_together = (('trade', 'instrument'),)
  
    id = models.AutoField(primary_key=True)
    zone_change_time = models.DateTimeField(auto_now_add=True)
    market_price = models.DecimalField(max_digits=10, decimal_places=2)
    trade = models.ForeignKey('Trade', on_delete=models.CASCADE)
    instrument = models.ForeignKey('Instrument', on_delete=models.PROTECT)
    PRICE_ZONE_CHOICES = [(tag.name, tag.value) for tag in PriceZone]
    existing_price_zone = EnumField(choices=PRICE_ZONE_CHOICES, default=PriceZone.RANGE.value)
    next_price_zone = EnumField(choices=PRICE_ZONE_CHOICES, default=PriceZone.RANGE.value)
    scanning_algo = models.ForeignKey('Algorithm', on_delete=models.PROTECT)


    @classmethod
    def add_indicator_entry(cls, *, market_price: float, trade_id: int, instrument_id: int, existing_price_zone: str, next_price_zone: str, zone_change_time: datetime,scanning_algo_name):
        # Validate market_price
        if not isinstance(market_price, float):
            raise ValidationError("market_price must be a float")

        # Validate trade_id and instrument_id
        try:
            trade = Trade.objects.get(id=trade_id)
            instrument = Instrument.objects.get(id=instrument_id)
        except ObjectDoesNotExist:
            raise ValidationError("Either trade_id or instrument_id does not exist")

        # Check if the trade session is active
        if not trade.is_active:
            raise ValidationError("The trade is not active")

        # Validate existing_price_zone and next_price_zone
        valid_zones = [zone.value for zone in PriceZone]
        if existing_price_zone not in valid_zones or next_price_zone not in valid_zones:
            raise ValidationError("Invalid price zone")

      # Get the Algorithm instance
        try:
            scanning_algo = Algorithm.objects.get(name=scanning_algo_name)  # Get the Algorithm instance using scanning algo name
        except ObjectDoesNotExist:
            raise ValidationError(f"Algorithm with name {scanning_algo_name} does not exist.")

        # Create and save the new record
        record = cls(
            market_price=market_price,
            trade=trade,
            instrument=instrument,
            existing_price_zone=existing_price_zone,
            next_price_zone=next_price_zone,
            zone_change_time=zone_change_time,
            scanning_alogo=scanning_algo
        )
        record.save()
