from django.urls import path
from integration_service.views.broker_view import register_broker, get_user_brokers, set_default_broker
from integration_service.views.kite_auth_view import set_session, get_login_url, get_profile_info
from integration_service.views.kite_integration_view import (
    get_historical_data, get_holdings, get_positions, get_orders, 
    get_order_trades, get_order_history, place_order, get_available_margin, get_quotes
)

urlpatterns = [
    # Broker management endpoints
    path('register_broker/', register_broker, name='register_broker'),
    path('get_user_brokers/', get_user_brokers, name='get_user_brokers'),
    path('set_default_broker/', set_default_broker, name='set_default_broker'),
    
    # Kite authentication endpoints
    path('set_session/', set_session, name='set_session'),
    path('get_login_url/', get_login_url, name='get_login_url'),
    path('get_profile_info/', get_profile_info, name='get_profile_info'),
    
    # Historical data endpoints
    path('get_historical_data/', get_historical_data, name='get_historical_data'),
    
    # Portfolio endpoints
    path('get_holdings/', get_holdings, name='get_holdings'),
    path('get_positions/', get_positions, name='get_positions'),
    path('get_orders/', get_orders, name='get_orders'),
    path('get_order_trades/', get_order_trades, name='get_order_trades'),
    path('get_order_history/', get_order_history, name='get_order_history'),
    path('place_order/', place_order, name='place_order'),
    path('get_available_margin/', get_available_margin, name='get_available_margin'),
    
    # Trade endpoints
    path('get_quotes/', get_quotes, name='get_quotes'),
] 