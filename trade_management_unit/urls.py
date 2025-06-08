from django.urls import path, re_path
# from django.urls import re_path

from .views import instrument_view, trade_session_view
from .consumers import trade_session_consumer

urlpatterns = [
    # Instrument endpoints - handle both with and without trailing slash
    re_path(r'^get_instruments/?$', instrument_view.get_instruments, name='get_instruments'),
    re_path(r'^update_instruments/?$', instrument_view.update_instruments, name='update_instruments'),
    
    # Trade session endpoints - handle both with and without trailing slash
    # re_path(r'^get_all_trades_info/?$', trade_session_view.get_all_trades_info, name='get_all_trades_info'),
    re_path(r'^initiate_trade_session/?$', trade_session_view.initiate_trade_session, name='initiate_trade_session'),
    re_path(r'^get_new_session_param_options/?$', trade_session_view.get_new_session_param_options, name='get_new_session_param_options'),
    re_path(r'^get_active_trade_sessions/?$', trade_session_view.get_active_trade_sessions, name='get_active_trade_sessions'),
    # re_path(r'^get_trade_sessions/?$', trade_session_view.get_trade_sessions, name='get_trade_sessions'),
    # re_path(r'^resume_trade_session/?$', trade_session_view.resume_trade_session, name='resume_trade_session'),
    # re_path(r'^session_active/?$', trade_session_view.session_active, name='session_active'),
    # re_path(r'^terminate_trade_session/?$', trade_session_view.terminate_trade_session, name='terminate_trade_session'),
    
]


