
from django.db import models

class Trade(models.Model):
    class Meta:
        db_table = "trades"
  
    id = models.CharField(auto_created=True,primary_key=True,blank=False,max_length=64,default="") 
    started_at = models.DateTimeField(blank=False)
    closed_at =  models.DateTimeField()
    stock =   models.ForeignKey("Stock", verbose_name="Ordered Stock", on_delete=models.CASCADE)   
    trade_session =   models.ForeignKey("TradeSession", verbose_name="Trade Session", on_delete=models.CASCADE, default=None)   
    is_active = models.BooleanField(default=True)
    trading_alog_id = models.CharField(blank=False,max_length=64,default="")
    net_profit = models.FloatField(blank=True, null=True)

