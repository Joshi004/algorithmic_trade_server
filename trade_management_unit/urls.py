from django.urls import path
# from django.urls import re_path

from .views import instrument_view, trade_session_view,kite_view
from .consumers import trade_session_consumer

urlpatterns = [
    path('get_instruments',instrument_view.get_instruments), # http://localhost:8000/tmu/update_instruments
    path('update_instruments',instrument_view.update_instruments),
    path('set_trade_price',trade_session_view.set_price),
    path('set_session',kite_view.set_session),    
    path('get_login_url',kite_view.get_login_url),    
    path('get_profile_info',kite_view.get_profile_info)    
] 


