from django.db import models
from django_mysql.models import EnumField
from trade_management_unit.Constants.TmuConstants import PriceZone  # assuming constants.py is in the same directory
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from trade_management_unit.models.Instrument import Instrument
from trade_management_unit.models.Trade import Trade

class AlgoSltoTrackRecord(models.Model):
    class Meta:
        db_table = "algo_slto_track_records"
  
    id = models.AutoField(primary_key=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    market_price = models.DecimalField(max_digits=10, decimal_places=2)
    trade = models.ForeignKey('Trade', on_delete=models.CASCADE)
    instrument = models.ForeignKey('Instrument', on_delete=models.CASCADE)

    PRICE_ZONE_CHOICES = [(tag.name, tag.value) for tag in PriceZone]
    existing_price_zone = EnumField(choices=PRICE_ZONE_CHOICES, default=PriceZone.RANGE.value)

    next_price_zone = EnumField(choices=PRICE_ZONE_CHOICES, default=PriceZone.RANGE.value)
    existing_price_zone_time = models.IntegerField(null=True)


    @classmethod
    def add_indicator_entry(cls, *, market_price, trade_id, instrument_id, existing_price_zone, next_price_zone, existing_price_zone_time=None):
        # Validate parameters
        if not isinstance(market_price, (int, float)):
            raise ValidationError("Market price must be a number.")

        try:
            trade = Trade.objects.get(id=trade_id)
        except ObjectDoesNotExist:
            raise ValidationError("Trade with given id does not exist.")

        try:
            instrument = Instrument.objects.get(id=instrument_id)
        except ObjectDoesNotExist:
            raise ValidationError("Instrument with given id does not exist.")

        if existing_price_zone not in [tag.value for tag in PriceZone]:
            raise ValidationError("Existing price zone is not valid.")

        if next_price_zone not in [tag.value for tag in PriceZone]:
            raise ValidationError("Next price zone is not valid.")

        if existing_price_zone_time is not None and not isinstance(existing_price_zone_time, int):
            raise ValidationError("Existing price zone time must be an integer or None.")

        # Create and save the Slto object
        slto = cls(
            market_price=market_price,
            trade=trade,
            instrument=instrument,
            existing_price_zone=existing_price_zone,
            next_price_zone=next_price_zone,
            existing_price_zone_time=existing_price_zone_time
        )
        slto.save()
