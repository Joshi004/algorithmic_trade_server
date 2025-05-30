from django.db import models


class ScanningAlgorithm(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    display_name = models.CharField(max_length=255, db_index=True, default=None)
    description = models.TextField()

    class Meta:
        db_table = "scanning_algorithms"
        verbose_name = "scanning algorithm"
        verbose_name_plural = "scanning algorithms"

    def __str__(self):
        return self.name

    @classmethod
    def get_name_by_id(cls, algorithm_id):
        try:
            return cls.objects.get(id=algorithm_id).name
        except cls.DoesNotExist:
            return None 