from django.db import models
from django_mysql.models import EnumField
from django.db.models import Sum
from trade_management_unit.lib.common.Utils.Utils import *
from django.db import transaction


class Trade(models.Model):
    class Meta:
        db_table = "trades"
  
    id = models.BigAutoField(auto_created=True, primary_key=True, blank=False) 
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(blank=False)
    closed_at = models.DateTimeField(blank=True, null=True)
    instrument = models.ForeignKey("Instrument", verbose_name="Ordered Instrument", on_delete=models.CASCADE)   
    trade_session = models.ForeignKey("TradeSession", verbose_name="Trade Session", on_delete=models.CASCADE, default=None)   
    net_profit = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    VIEW_CHOICES=[("long","long"),("short","short")]
    view = EnumField(choices=VIEW_CHOICES,default = "long")
    user_id = models.CharField(max_length=64,default="1")

    @classmethod
    def fetch_active_trade(cls, instrument_id, trade_session_id, user_id):
        try:
            trade = cls.objects.get(
                instrument_id=instrument_id,
                trade_session_id=trade_session_id,
                user_id=user_id,
                is_active=True
            )
            return trade
        except cls.DoesNotExist:
            return None

    @classmethod
    def fetch_or_initiate_trade(cls, instrument_id, action, trade_session_id, user_id):
        with transaction.atomic():
            trade, created = cls.objects.select_for_update().get_or_create(
                instrument_id=instrument_id,
                trade_session_id=trade_session_id,
                user_id=user_id,
                is_active=True,
                defaults={
                    'started_at': current_ist(),
                    'closed_at': None,
                    'view': 'long' if action == 'buy' else 'short',
                }
            )
        return trade

    @classmethod
    def initiate_trade(cls, instrument_id, action, trade_session_id, user_id):
        trade = cls(
                instrument_id=instrument_id,
                trade_session_id=trade_session_id,
                user_id=user_id,
                is_active=True,
                started_at= current_ist(),
                closed_at= None,
                view='long' if action == 'buy' else 'short'
            )
        trade.save()
        return trade

    @classmethod
    def update_trade(cls, trade_id, **kwargs):
        trade = cls.objects.get(id=trade_id)
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
                net_profit -= (order.price * order.quantity)
            elif order.order_type == 'sell':
                net_profit += (order.price * order.quantity)
            net_profit -= order.frictional_losses
        return net_profit

    @classmethod
    def fetch_active_trades_for_trade_session(cls, trade_session_id):
        return cls.objects.filter(trade_session_id=trade_session_id, is_active=True)



    
