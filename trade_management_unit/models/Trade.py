from django.db import models
from django_mysql.models import EnumField
from django.db.models import Sum
from datetime import datetime
from django.db.models import Q
from trade_management_unit.models.Instrument import Instrument
from trade_management_unit.Constants.TmuConstants import *
class Trade(models.Model):
    class Meta:
        db_table = "trades"
  
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False) 
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(blank=False)
    closed_at = models.DateTimeField(blank=True, null=True)
    instrument = models.ForeignKey("Instrument", verbose_name="Ordered Instrument", on_delete=models.CASCADE)   
    trade_session = models.ForeignKey("TradeSession", verbose_name="Trade Session", on_delete=models.CASCADE, default=None)   
    net_profit = models.FloatField(blank=True, null=True)
    dummy = models.BooleanField(default=False)
    VIEW_CHOICES=[("long","long"),("short","short")]
    view = EnumField(choices=VIEW_CHOICES,default = "long")
    user_id = models.CharField(max_length=64,default="1")
    max_price = models.FloatField(blank=True, null=True)
    min_price = models.FloatField(blank=True, null=True)
    margin = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    @classmethod
    def fetch_active_trade(cls, instrument_id,trade_session_id, user_id, dummy):
        try:
            trade = cls.objects.get(
                instrument_id=instrument_id,
                trade_session_id=trade_session_id,
                user_id=user_id,
                is_active=True,
                dummy=dummy
            )
            return trade
        except cls.DoesNotExist:
            return None


    @classmethod
    def fetch_or_initiate_trade(cls, instrument_id, action, trade_session_id, user_id, dummy,margin):
        try:
            # Try to find an existing active trade with the same parameters
            trade = cls.objects.get(
                instrument_id=instrument_id,
                trade_session_id=trade_session_id,
                user_id=user_id,
                is_active=True
            )
        except cls.DoesNotExist:
            # If no existing trade is found, create a new one
            trade = cls(
                is_active=True,
                started_at=datetime.now(),
                closed_at=None,
                instrument_id=instrument_id,
                trade_session_id=trade_session_id,
                view='long' if action == 'buy' else 'short',
                user_id=user_id,
                dummy=dummy,
                max_price=None,
                min_price=None,
                margin = round(margin,2)
            )
            trade.save()
        return trade


    @classmethod
    def update_trade(cls, trade_id, **kwargs):
        trade = cls.objects.get(id=trade_id)
        if 'max_price' in kwargs:
            trade.max_price = kwargs['max_price']
        if 'min_price' in kwargs:
            trade.min_price = kwargs['min_price']
        if 'is_active' in kwargs:
            trade.is_active = kwargs['is_active']
        if 'closed_at' in kwargs:
            trade.closed_at = kwargs['closed_at']
        trade.save()
        return trade.id


    @classmethod
    def get_net_profit(cls, trade_id):
        trade = cls.objects.get(id=trade_id)
        orders = trade.order_set.all()
        net_profit = 0
        for order in orders:
            if order.order_type == 'buy':
                net_profit -= order.price
            elif order.order_type == 'sell':
                net_profit += order.price
            net_profit -= order.frictional_losses
        return net_profit

    @classmethod
    def get_total_margin(cls, user_id,dummy):
        total_margin = cls.objects.filter(user_id=user_id, is_active=True,dummy=dummy).aggregate(total_margin=Sum('margin'))['total_margin']
        return total_margin if total_margin else 0



    
