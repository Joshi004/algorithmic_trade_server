import json
import time
from datetime import datetime
from django.db.models import Q
from urllib.parse import parse_qs
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from trade_management_unit.models.Instrument import Instrument
from trade_management_unit.lib.Kite.KiteTickhandler import KiteTickhandler
import threading

from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoFactory import TrackerAlgoFactory
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession

class TradeSessionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        query_params = self._parse_query_params()
        # trading_symbols = query_params.get('trading_symbols', [])
        # exchange = query_params.get('exchange', '')
        trade_session_id = query_params.get('trade_session_id', '')


        
        # Connect tO Clent established 
        # trading_freq = "10minute"
        # user_id = "1"
        # dummy = True
        print("!!! Add UserS PRofile And also add cotracint in all tables using user id ")
                #
        trade_session_identifier = "trade_session__"+str(trade_session_id)
        


        self.room_group_name = str(trade_session_identifier)
        await self._add_to_group_and_accept()
        
        await self.send(text_data=json.dumps({"connected": True}))

    # def start_threaded_trade_session(self,user_id,scanning_algorithm_name,tracking_algorithm_name,trading_freq,kite_tick_handler,kit_connect_object,dummy):
    #     self.trade_session = TradeSession(user_id,scanning_algorithm_name,tracking_algorithm_name,trading_freq,dummy,kite_tick_handler,kit_connect_object)
    #
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def send_data(self, data):
        # try:
        await self.send(text_data=json.dumps(data))
        # except Exception as e:
        #     print("Error sending response via socket:", e)

    def _parse_query_params(self):
        query_string = self.scope['query_string'].decode('utf8')
        query_params = parse_qs(query_string)
        trade_session_id = query_params.get('trade_session_id', [''])[0]
        # trading_symbols = [symbol for symbol in trading_symbols_str.split(',') if symbol]
        # exchange = query_params.get('exchange', [''])[0]
        #
        # tracking_algorithm = query_params.get('tracking_algorithm', [''])[0]
        # scanning_algorithm = query_params.get('scanning_algorithm', [''])[0]
        
        return {
            'trade_session_id': trade_session_id,
        }


    async def _add_to_group_and_accept(self):
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
