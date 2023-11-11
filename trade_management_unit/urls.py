from django.urls import path
# from django.urls import re_path

from .views import instrument_view, trade_view,kite_view, scanner_algo_view, portfolio_view,trade_session_view
from .consumers import trade_session_consumer

urlpatterns = [
    path('get_instruments',instrument_view.get_instruments), # http://localhost:8000/tmu/update_instruments
    path('update_instruments',instrument_view.update_instruments),
    path('fetch_historical_data',instrument_view.fetch_historical_data),
    path('get_quotes',trade_view.get_quotes),
    path('set_session',kite_view.set_session),    
    path('get_login_url',kite_view.get_login_url),    
    path('get_profile_info',kite_view.get_profile_info),    
    path('get_eligible_instruments',scanner_algo_view.get_eligible_instruments),    
    path('get_udts_eligibility',scanner_algo_view.get_udts_eligibility),    
    path('get_holdings',portfolio_view.get_holdings),    
    path('get_positions',portfolio_view.get_positions),    
    path('get_orders',portfolio_view.get_orders),    
    path('get_orders_trades',portfolio_view.get_orders_trades),    
    path('get_order_history',portfolio_view.get_order_history),    
    path('place_order',portfolio_view.place_order),
    path('initiate_trade_session',trade_session_view.initiate_trade_session),
    path('get_new_session_param_options',trade_session_view.get_new_session_param_options)
]


