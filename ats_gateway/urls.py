from django.urls import path, re_path
from .views import GatewayView

urlpatterns = [
    # Use the new factory-based GatewayView as the main entry point
    re_path(r'^(?P<path>.+)$', GatewayView.as_view(), name='gateway'),

] 