
from django.db import models

class TradeSession(models.Model):
    class Meta:
        db_table = "trade_sessions"
  
    id = models.CharField(primary_key=True,blank=False,max_length=64,default="") 
    started_at = models.DateTimeField(blank=False)
    closed_at =  models.DateTimeField()
    net_profit = models.FloatField()
    is_closed = models.BooleanField(default=False) 

