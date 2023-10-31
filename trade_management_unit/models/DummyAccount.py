from django.db import models
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
