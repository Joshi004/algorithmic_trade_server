from django.urls import path, re_path
from .views import GatewayView, RegistrationView

urlpatterns = [
    # Registration endpoint
    path('register/', RegistrationView.as_view(), name='register'),
    
    # Use the factory-based GatewayView as the main entry point for all other paths
    re_path(r'^(?P<path>.+)$', GatewayView.as_view(), name='gateway'),
] 