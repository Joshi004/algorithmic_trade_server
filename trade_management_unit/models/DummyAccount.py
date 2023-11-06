from django.db import models
from trade_management_unit.models.Trade import Trade
from django.utils import timezone

class DummyAccount(models.Model):    
    id = models.AutoField(primary_key=True)
    user_id = models.CharField(max_length=200, db_index=True)  # Index added
    initial_balance = models.DecimalField(max_digits=10, decimal_places=2)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2)
    last_balance_refreshed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dummy_accounts"

    @classmethod
    def get_attribute(cls, user_id, attribute):
        try:
            user = cls.objects.get(user_id=user_id)
            return getattr(user, attribute, None)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_current_balance_including_margin(cls,user_id,dummy):
        current_amount = float(cls.objects.get(user_id=user_id).current_balance)
        existing_margin_used = float(Trade.get_total_margin(user_id,dummy))
        return (current_amount  - existing_margin_used)

