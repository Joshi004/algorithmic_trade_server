from django.db import models
from django_mysql.models import EnumField

class Trade(models.Model):
    class Meta:
        db_table = "trades"
  
    id = models.CharField(auto_created=True, primary_key=True, blank=False, max_length=64, default="") 
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(blank=False)
    closed_at = models.DateTimeField()
    instrument = models.ForeignKey("Instrument", verbose_name="Ordered Instrument", on_delete=models.CASCADE)   
    trade_session = models.ForeignKey("TradeSession", verbose_name="Trade Session", on_delete=models.CASCADE, default=None)   
    net_profit = models.FloatField(blank=True, null=True)
    dummy = models.BooleanField(default=False)
    VIEW_CHOICES=[("long","long"),("short","short")]
    view = EnumField(choices=VIEW_CHOICES,default = "long")
    user_id = models.CharField(max_length=64,default="1")
    max_price = models.FloatField(blank=True, null=True)
    min_price = models.FloatField(blank=True, null=True)
