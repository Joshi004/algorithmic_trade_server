from django.urls import path
# from django.urls import re_path

from .views import stock_view, trade_session_view
from .consumers import trade_session_consumer

urlpatterns = [
    path('update_stocks',stock_view.fetch_and_update_stocks), # http://localhost:8000/tmu/update_stocks
    path('get_all_stocks',stock_view.get_stocks_list)
] 

# websocket_urlpatterns = [
#     path('ws/test/', trade_session_consumer.TradeSession.as_asgi()),
# ]

# urlpatterns += websocket_urlpatterns

