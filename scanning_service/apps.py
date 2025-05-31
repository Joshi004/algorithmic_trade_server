from django.apps import AppConfig


class ScanningServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scanning_service'
    verbose_name = 'Scanning Service'
    
    def ready(self):
        """Called when Django starts"""
        # Import any signal handlers or startup code here if needed
        pass
