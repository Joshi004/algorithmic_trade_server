from enum import Enum
from django.db import models
from datetime import datetime
from django_mysql.models import EnumField
from django.core.exceptions import ValidationError

class Order(models.Model):
    class Meta:
        db_table = "orders"
 

    STATUS_CHOICES=[("pending","pending"),("rejected","rejected"),("exicuted","exicuted")]
    ORDER_TYPES=[("buy","buy"),("sell","sell")]
    id = models.CharField(auto_created=True,primary_key=True,blank=False,max_length=64,default="")
    status = EnumField(choices=STATUS_CHOICES,default="pending")
    order_type = EnumField(choices=ORDER_TYPES)
    started_at = models.DateTimeField(default=datetime.now,blank=False)
    closed_at = models.DateTimeField(blank=True,null=True,default=datetime.now)
    instrument =   models.ForeignKey("Instrument", verbose_name="instrument_id", on_delete=models.CASCADE)
    trade =   models.ForeignKey("Trade", verbose_name="trade_id", on_delete=models.CASCADE)
    dummy = models.BooleanField(default=False)
    kite_order_id = models.CharField(max_length=64, blank=True, null=True)
    frictional_losses = models.FloatField(blank=True, null=True)
    user_id = models.CharField(max_length=64, blank=False,default="1")
    quantity = models.IntegerField(default=1)


    def clean(self):
        # If it's not a dummy order, kite_order_id must not be null
        if not self.dummy and self.kite_order_id is None:
            raise ValidationError("kite_order_id can't be null unless it's a dummy order.")

    @classmethod
    def initiate_order(cls, order_type, instrument_id, trade_id, dummy, kite_order_id, frictional_losses, user_id, quantity):
        order = cls(
            status='pending',
            order_type=order_type,
            started_at=datetime.now(),
            closed_at=None,
            instrument_id=instrument_id,
            trade_id=trade_id,
            dummy=dummy,
            kite_order_id=kite_order_id if not dummy else None,
            frictional_losses=frictional_losses,
            user_id=user_id,
            quantity=quantity
        )
        order.clean()
        order.save()
        return order.id


