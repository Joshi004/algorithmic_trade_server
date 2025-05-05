from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class UserConfiguration(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(unique=True)
    risk_appetite = models.FloatField(default=5, validators=[MinValueValidator(0), MaxValueValidator(100)])
    min_reward_risk_ratio = models.FloatField(default=2)
    max_reward_risk_ratio = models.FloatField(default=20)
    trades_per_session = models.IntegerField(default=100)
    api_key = models.CharField(max_length=255, null=True, blank=True)
    api_secret = models.CharField(max_length=255, null=True, blank=True)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    class Meta:
        db_table = "user_configurations"


    @classmethod
    def get_attribute(cls, user_id, attribute):
        try:
            user_config = cls.objects.get(user_id=user_id)
            return getattr(user_config, attribute, None)
        except cls.DoesNotExist:
            return None

    @classmethod
    def set_attribute(cls, user_id, attribute, value):
        user_config, created = cls.objects.get_or_create(user_id=user_id)
        setattr(user_config, attribute, value)
        user_config.save()
        return user_config
