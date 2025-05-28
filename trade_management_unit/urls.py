from django.urls import path
# from django.urls import re_path

from .views import instrument_view, scanner_algo_view, trade_session_view
from .consumers import trade_session_consumer

urlpatterns = [
    path('get_instruments', instrument_view.get_instruments), # http://localhost:8000/tmu/update_instruments
    path('update_instruments', instrument_view.update_instruments),
    path('get_historical_data', instrument_view.get_historical_data),
    path('get_all_trades_info', trade_session_view.get_all_trades_info),
    path('get_eligible_instruments', scanner_algo_view.get_eligible_instruments),
    path('get_udts_eligibility', scanner_algo_view.get_udts_eligibility),
    path('get_udts_redcord', scanner_algo_view.get_udts_redcord),
    path('initiate_trade_session', trade_session_view.initiate_trade_session),
    path('get_new_session_param_options', trade_session_view.get_new_session_param_options),
    path('get_trade_sessions', trade_session_view.get_trade_sessions),
    path('resume_trade_session', trade_session_view.resume_trade_session),
    path('session_active', trade_session_view.session_active),
    path('terminate_trade_session', trade_session_view.terminate_trade_session)
]


