from django.db import models
from django.utils import timezone


class ScanningAlgorithm(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    display_name = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    parameters_schema = models.JSONField(default=dict, blank=True, help_text='Algorithm configuration parameters')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scanning_algorithms"
        verbose_name = "Scanning Algorithm"
        verbose_name_plural = "Scanning Algorithms"
        ordering = ['name']

    def __str__(self):
        return self.display_name or self.name

    @classmethod
    def get_name_by_id(cls, algorithm_id):
        try:
            return cls.objects.get(id=algorithm_id).name
        except cls.DoesNotExist:
            return None
            
    @classmethod
    def get_active_algorithms(cls):
        """Get all active scanning algorithms"""
        return cls.objects.filter(is_active=True)
        
    def get_parameters(self):
        """Get algorithm parameters or empty dict if none"""
        return self.parameters_schema or {} 