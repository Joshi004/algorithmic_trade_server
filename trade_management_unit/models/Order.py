
from enum import Enum
from django.db import models
from datetime import datetime

# class Status(Enum):
#     Pending = "Pending"
#     Exicuted = "Exicuted"
#     Rejected = "Rejected"

class Order(models.Model):
    class Meta:
        db_table = "orders"
  
    id = models.CharField(auto_created=True,primary_key=True,blank=False,max_length=64,default="")
    # types = Enum (buy,sell)
    # status = (pending,rejected,executed)
    startted_at = models.DateTimeField(default=datetime.now,blank=False)
    closed_at = models.DateTimeField(blank=True,default=datetime.now)
    stock =   models.ForeignKey("Stock", verbose_name="stock_id", on_delete=models.CASCADE)
    trade =   models.ForeignKey("Trade", verbose_name="trade_id", on_delete=models.CASCADE)
    

    