from django.urls import path, re_path
from integration_service.views.broker_view import register_broker, get_user_brokers, set_default_broker
from integration_service.views.kite_auth_view import set_session, get_login_url, get_profile_info
from integration_service.views.kite_integration_view import (
    get_historical_data, get_holdings, get_positions, get_orders, 
    get_order_trades, get_order_history, place_order, get_available_margin, get_quotes, get_instruments
)

urlpatterns = [
    # Broker management endpoints - handle both with and without trailing slash
    re_path(r'^register_broker/?$', register_broker, name='register_broker'),
    re_path(r'^get_user_brokers/?$', get_user_brokers, name='get_user_brokers'),
    re_path(r'^set_default_broker/?$', set_default_broker, name='set_default_broker'),
    
    # Kite authentication endpoints - handle both with and without trailing slash
    re_path(r'^set_session/?$', set_session, name='set_session'),
    re_path(r'^get_login_url/?$', get_login_url, name='get_login_url'),
    re_path(r'^get_profile_info/?$', get_profile_info, name='get_profile_info'),
    
    # Historical data endpoints - handle both with and without trailing slash
    re_path(r'^get_historical_data/?$', get_historical_data, name='get_historical_data'),
    
    # Portfolio endpoints - handle both with and without trailing slash
    re_path(r'^get_holdings/?$', get_holdings, name='get_holdings'),
    re_path(r'^get_positions/?$', get_positions, name='get_positions'),
    re_path(r'^get_orders/?$', get_orders, name='get_orders'),
    re_path(r'^get_order_trades/?$', get_order_trades, name='get_order_trades'),
    re_path(r'^get_order_history/?$', get_order_history, name='get_order_history'),
    re_path(r'^place_order/?$', place_order, name='place_order'),
    re_path(r'^get_available_margin/?$', get_available_margin, name='get_available_margin'),
    
    # Trade endpoints - handle both with and without trailing slash
    re_path(r'^get_quotes/?$', get_quotes, name='get_quotes'),
    
    # Instruments endpoints - handle both with and without trailing slash
    re_path(r'^get_instruments/?$', get_instruments, name='get_instruments'),
] 