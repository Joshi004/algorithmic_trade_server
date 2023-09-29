from django.db import models
from django_mysql.models import EnumField
from trade_management_unit.Constants.TmuConstants import PriceZone  # assuming constants.py is in the same directory

class Slto(models.Model):
    class Meta:
        db_table = "algo_slto_track_records"
  
    id = models.AutoField(primary_key=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    market_price = models.DecimalField(max_digits=10, decimal_places=2)
    trade = models.ForeignKey('Trade', on_delete=models.CASCADE)

    # New fields
    instrument = models.ForeignKey('Instrument', on_delete=models.CASCADE)
    PRICE_ZONE_CHOICES = [(tag.name, tag.value) for tag in PriceZone]
    existing_price_zone = EnumField(choices=PRICE_ZONE_CHOICES, default=PriceZone.RANGE.value)
    next_price_zone = EnumField(choices=PRICE_ZONE_CHOICES, default=PriceZone.RANGE.value)
    existing_price_zone_time = models.IntegerField(null=True)
