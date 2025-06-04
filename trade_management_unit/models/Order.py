from django.db import models
from django_mysql.models import EnumField
from django.core.exceptions import ValidationError
from trade_management_unit.lib.common.Utils.Utils import *
from django.db import transaction
from trade_management_unit.lib.common.Utils.custome_logger import log

class Order(models.Model):
    class Meta:
        db_table = "orders"
        unique_together = (('trade', 'order_type'),)


    STATUS_CHOICES=[("pending","pending"),("rejected","rejected"),("exicuted","exicuted")]
    ORDER_TYPES=[("buy","buy"),("sell","sell")]
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False)
    status = EnumField(choices=STATUS_CHOICES,default="pending")
    order_type = EnumField(choices=ORDER_TYPES)
    started_at = models.DateTimeField(default=current_ist,blank=False)
    closed_at = models.DateTimeField(blank=True,null=True,default=current_ist)
    instrument = models.ForeignKey("Instrument", verbose_name="instrument_id", on_delete=models.CASCADE)
    trade = models.ForeignKey("Trade", verbose_name="trade_id", on_delete=models.CASCADE)
    trade_session = models.ForeignKey("TradeSession", verbose_name="trade_session_id", on_delete=models.CASCADE)
    dummy = models.BooleanField(default=False)
    kite_order_id = models.CharField(max_length=64, blank=True, null=True)
    frictional_losses = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    user_id = models.CharField(max_length=64, blank=False,default="1")
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)


    @classmethod
    def initiate_order(cls, order_type, instrument_id, trade_id, dummy, kite_order_id, frictional_losses, user_id, quantity, price, trade_session_id):
        # Locking The table can cause slow down if used excisivly
        with transaction.atomic():
            existing_order = cls.objects.select_for_update().filter(trade_id=trade_id, order_type=order_type).first()
            if existing_order:
                return existing_order

            kite_order_id = None if dummy else kite_order_id
            order = cls(
                status='exicuted',
                order_type=order_type,
                started_at=current_ist(),
                closed_at=current_ist(),
                instrument_id=instrument_id,
                trade_id=trade_id,
                dummy=dummy,
                kite_order_id=kite_order_id,
                frictional_losses=frictional_losses,
                user_id=user_id,
                quantity=quantity,
                price=price,
                trade_session_id=trade_session_id
            )
            order.save()
            return order



    @classmethod
    def fetch_order(cls,  trade_id: int) -> models.Model:
        # Validate data integrity
        if not cls.objects.filter(trade_id=trade_id).exists():
            raise ValidationError(f"No trade found with id {trade_id}.")

        try:
            result = cls.objects.get(trade_id=trade_id)
            return result

        except Exception as e:
            log(f'Multiple orders found: {str(e)}', 'error')
            raise ValidationError("No matching order found.")
