from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class UserConfiguration(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(unique=True)
    risk_appetite = models.FloatField(default=5, validators=[MinValueValidator(0), MaxValueValidator(100)])
    reward_risk_ratio = models.FloatField(default=2)

    class Meta:
        db_table = "user_configurations"


    @classmethod
    def get_attribute(cls, user_id, attribute):
        try:
            user_config = cls.objects.get(user_id=user_id)
            return getattr(user_config, attribute, None)
        except cls.DoesNotExist:
            return None