from django.db import models
from enum import Enum

class AlgorithmType(Enum):
    TRACKING = "tracking"
    SCANNING = "scanning"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

class Algorithm(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True, unique=True)  # Made this field unique
    table_name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20,
        choices=AlgorithmType.choices(),
        default=AlgorithmType.TRACKING.value,
    )
    description = models.TextField()

    class Meta:
        verbose_name = "algorithm"
        verbose_name_plural = "algorithms"
        db_table = 'algorithms'

    def __str__(self):
        return self.name
    

    @classmethod
    def get_id_by_name(cls, name):
        try:
            return cls.objects.get(name=name).id
        except cls.DoesNotExist:
            return None
