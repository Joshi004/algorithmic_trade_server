
from django.db import models

class TradeSession(models.Model):
    class Meta:
        db_table = "trade_sessions"
  
    id = models.CharField(auto_created=True,primary_key=True,blank=False,max_length=64,default="") 
    started_at = models.DateTimeField(blank=False)
    closed_at =  models.DateTimeField(blank=True,null=True)
    net_profit = models.FloatField(blank=True,null=True)
    is_closed = models.BooleanField(default=False)
    scanning_alogo_id = models.IntegerField(blank=False,default=1)


