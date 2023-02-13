from email.policy import default
from django.db import models

class Stock(models.Model):
    class Meta:
        db_table = "stocks"
    
    id = models.CharField(primary_key=True,blank=False,max_length=64,default="") 
    nse_symbol = models.CharField(unique=True, blank=False,max_length=128,default="") 
    name = models.CharField(blank=False,max_length=256,default="")
    series = models.CharField(blank=False,max_length=10,default="EQ")
    listing_date = models.DateField(blank=True,default="1990-01-01")
    paid_up_value = models.IntegerField(blank=True,default=1)
    market_lot = models.IntegerField(blank=True, default=1)
    market_lot = models.IntegerField(blank=True, default=1)
    isin_number = models.CharField(unique=True, blank=False,max_length=64,default=None)
    face_value = models.IntegerField(blank=False,default=10)


