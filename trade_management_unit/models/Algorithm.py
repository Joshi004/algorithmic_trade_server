from django.db import models
from django.utils.translation import ugettext_lazy as _
from enum import Enum

class AlgorithmType(Enum):
    TRACKING = "tracking"
    SCANNING = "scanning"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

class Algorithm(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True)  # Added db_index=True here
    table_name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20,
        choices=AlgorithmType.choices(),
        default=AlgorithmType.TRACKING.value,
    )
    description = models.TextField()

    class Meta:
        verbose_name = _("algorithm")
        verbose_name_plural = _("algorithms")
        db_table = 'algorithms'

    def __str__(self):
        return self.name
