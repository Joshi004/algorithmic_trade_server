from django.db import models

class Slto(models.Model):
    class Meta:
        db_table = "algo_slto_track_records"
  
    id = models.AutoField(primary_key=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    market_price = models.DecimalField(max_digits=10, decimal_places=2)
    trade = models.ForeignKey('Trade', on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)
