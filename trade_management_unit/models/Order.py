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
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False)
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


    @classmethod
    def initiate_order(cls, order_type, instrument_id, trade_id, dummy, kite_order_id, frictional_losses, user_id, quantity):
        kite_order_id = None if dummy else kite_order_id
        order = cls(
            status='exicuted',
            order_type=order_type,
            started_at=datetime.now(),
            closed_at=datetime.now(),
            instrument_id=instrument_id,
            trade_id=trade_id,
            dummy=dummy,
            kite_order_id=kite_order_id,
            frictional_losses=frictional_losses,
            user_id=user_id,
            quantity=quantity
        )
        order.save()
        return order

    @classmethod
    def fetch_order(cls, instrument_id: int, trade_id: int, dummy: bool, user_id: str) -> models.Model:
        # Validate data integrity
        if not cls.objects.filter(instrument_id=instrument_id).exists():
            raise ValidationError(f"No instrument found with id {instrument_id}.")
        if not cls.objects.filter(trade_id=trade_id).exists():
            raise ValidationError(f"No trade found with id {trade_id}.")

        try:
            return cls.objects.get(instrument_id=instrument_id, trade_id=trade_id, dummy=dummy, user_id=user_id)
        except cls.DoesNotExist:
            raise ValidationError("No matching order found.")



