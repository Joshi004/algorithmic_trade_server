from django.http import JsonResponse
from trade_management_unit.lib.Trade.trade import Trade
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession
from trade_management_unit.lib.TradeSession.TradeSessionHelper import TradeSessionHelper
from channels.generic.websocket import AsyncWebsocketConsumer
from django.forms.models import model_to_dict
from trade_management_unit.models.Algorithm import Algorithm
from trade_management_unit.lib.Kite.KiteTickhandler import KiteTickhandler

from trade_management_unit.Constants.TmuConstants import *


def initiate_trade_session(request,*args,**kwvrgs):
        query_paramas  =  request.GET
        trading_frequency = query_paramas.get("trading_frequency")
        user_id = query_paramas.get("user_id")
        dummy = bool(query_paramas.get("dummy"))
        scanning_algorithm_name = query_paramas.get("scanning_algorithm_name")
        tracking_algorithm_name = query_paramas.get("tracking_algorithm_name")
        print("!!! Add UserS PRofile And also add cotracint in all tables using user id ")
        kite_tick_handler = KiteTickhandler()
        kit_connect_object = kite_tick_handler.get_kite_ticker_instance()
        kit_connect_object.connect(threaded=True)

        trade_session_identifier = str(dummy)+ "__" +user_id + "__" + scanning_algorithm_name + "__" + tracking_algorithm_name + "__" + trading_frequency
        trade_session = TradeSession(user_id,scanning_algorithm_name,tracking_algorithm_name,trading_frequency,dummy,kite_tick_handler,kit_connect_object)
        response = {"trade_session_id":trade_session.trade_session_id}
        return JsonResponse(response,status=200, content_type='application/json')

def get_new_session_param_options(request):
        scanning_algorithms  = list(Algorithm.objects.filter(type="scanning").values())
        tracking_algorithms  = list(Algorithm.objects.filter(type="tracking").values())
        trading_frequencies =list( FREQUENCY_STEPS.keys())
        response = {
                "scanning_algorithms":scanning_algorithms,
                "tracking_algorithms":tracking_algorithms,
                "trading_frequencies":trading_frequencies,
                }
        return JsonResponse(response,status=200, content_type='application/json')

def get_trade_sessions(request):
    query_params = request.GET
    response = TradeSessionHelper().fetch_trade_session_info(query_params)
    return JsonResponse(response, status=200, content_type='application/json')




