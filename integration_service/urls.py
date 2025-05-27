from django.urls import path
from integration_service.views.broker_view import register_broker, get_user_brokers, set_default_broker

urlpatterns = [
    path('register_broker/', register_broker, name='register_broker'),
    path('get_user_brokers/', get_user_brokers, name='get_user_brokers'),
    path('set_default_broker/', set_default_broker, name='set_default_broker'),
] 