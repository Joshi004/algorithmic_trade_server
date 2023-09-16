from django.urls import path
# from django.urls import re_path

from .views import instrument_view, trade_view,kite_view, scanner_algo_view
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
    path('get_udts_eligibility',scanner_algo_view.get_udts_eligibility)    
]


