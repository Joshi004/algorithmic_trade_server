from django.db import models
from django.utils import timezone


class SeedTracker(models.Model):
    seed_name = models.CharField(
        max_length=255, 
        unique=True, 
        help_text='Name of the seed file that was applied'
    )
    applied_at = models.DateTimeField(
        default=timezone.now,
        help_text='When the seed was applied'
    )

    class Meta:
        db_table = "seed_tracker"
        verbose_name = "Seed Tracker"
        verbose_name_plural = "Seed Trackers"
        ordering = ['-applied_at']

    def __str__(self):
        return f"Seed: {self.seed_name} applied at {self.applied_at}"

    @classmethod
    def is_seed_applied(cls, seed_name):
        """Check if a seed was already applied"""
        return cls.objects.filter(seed_name=seed_name).exists()

    @classmethod
    def mark_seed_as_applied(cls, seed_name):
        """Mark a seed as applied"""
        obj, created = cls.objects.get_or_create(
            seed_name=seed_name,
            defaults={'applied_at': timezone.now()}
        )
        return obj, created 