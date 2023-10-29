from django.db import models

class Instrument(models.Model):    
    id = models.BigIntegerField(primary_key=True)
    instrument_token = models.BigIntegerField()
    exchange_token = models.BigIntegerField()
    trading_symbol = models.CharField(max_length=200, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    last_price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry = models.DateField(null=True)
    strike = models.DecimalField(max_digits=10, decimal_places=2)
    tick_size = models.DecimalField(max_digits=10, decimal_places=4)
    lot_size = models.IntegerField()
    instrument_type = models.CharField(max_length=50)
    segment = models.CharField(max_length=50)
    exchange = models.CharField(max_length=50, db_index=True)

    class Meta:
        db_table = "instruments"
        indexes = [
            models.Index(fields=['trading_symbol',]),
            models.Index(fields=['name',]),
            models.Index(fields=['exchange',]),
        ]
