from django.urls import path, re_path
from .views import GatewayView, register, login

urlpatterns = [
    # Registration endpoint
    path('register/', register, name='register'),
    # Login endpoint
    path('login/', login, name='login'),
    
    # Use the factory-based GatewayView as the main entry point for all other paths
    re_path(r'^(?P<path>.+)$', GatewayView.as_view(), name='gateway'),
] 
