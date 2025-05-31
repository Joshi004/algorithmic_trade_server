from django.apps import AppConfig


class InitiationServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'initiation_service'
    verbose_name = 'Initiation Service'
    
    def ready(self):
        """Called when Django starts"""
        # Import any signal handlers or startup code here if needed
        pass
