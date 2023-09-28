from enum import Enum
from django.db import models
from datetime import datetime
from django_mysql.models import EnumField

class Order(models.Model):
    class Meta:
        db_table = "orders"
 

    STATUS_CHOICES=[("pending","pending"),("rejected","rejected"),("exicuted","exicuted")]
    ORDER_TYPES=[("buy","buy"),("sell","sell")]
    id = models.CharField(auto_created=True,primary_key=True,blank=False,max_length=64,default="")
    status = EnumField(choices=STATUS_CHOICES,default="pending")
    order_type = EnumField(choices=ORDER_TYPES)
    started_at = models.DateTimeField(default=datetime.now,blank=False)
    closed_at = models.DateTimeField(blank=True,default=datetime.now)
    instrument =   models.ForeignKey("Instrument", verbose_name="instrument_id", on_delete=models.CASCADE)
    trade =   models.ForeignKey("Trade", verbose_name="trade_id", on_delete=models.CASCADE)
    dummy = models.BooleanField(default=False)
    kite_order_id = models.CharField(max_length=64, blank=True, null=True)
    frictional_losses = models.FloatField(blank=True, null=True)
    user_id = models.CharField(max_length=64, blank=False,default="1")
