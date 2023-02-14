
from enum import Enum
from django.db import models


# class Status(Enum):
#     Pending = "Pending"
#     Exicuted = "Exicuted"
#     Rejected = "Rejected"

class Order(models.Model):
    class Meta:
        db_table = "orders"
  
    id = models.CharField(primary_key=True,blank=False,max_length=64,default="") 
    trade =   models.ForeignKey("Trade", verbose_name="Trade ID", on_delete=models.CASCADE)
    

    