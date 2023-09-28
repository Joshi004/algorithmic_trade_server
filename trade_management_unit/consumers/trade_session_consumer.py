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

from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoFactory import TrackerAlgoFactory
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession

class TradeSessionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        query_params = self._parse_query_params()
        trading_symbols = query_params.get('trading_symbols', [])
        exchange = query_params.get('exchange', '')
        scanning_algorithm_name = query_params.get('scanning_algorithm', '')
        tracking_algorithm_name = query_params.get('tracking_algorithm', '')


        
        # Connect tO Clent established 
        trading_freq = "day"
        user_id = "joshi004"
        
        kite_tick_handler =  KiteTickhandler()
        kit_connect_object = kite_tick_handler.get_kite_ticker_instance()
        kit_connect_object.connect()
        trade_session = TradeSession(user_id,scanning_algorithm_name,tracking_algorithm_name,trading_freq,kite_tick_handler,kit_connect_object)

        self.room_group_name = str(trade_session)
        await self._add_to_group_and_accept()
        
        # tracker_algo_object = TrackerAlgoFactory().get_instance(self.room_group_name)
        # tracker_algo_object.set_algorithm(tracker_object) #This will add indicators to the tracker_object
        # tracker_object.get_kite_ticker_instance().connect()
        
        # scanner_object = ScannerAlgoFactory().get_scanner(scanning_algorithm_name)
        # scanner_object.set_trade_frequency("day")
        # scanner_object.set_tracker_session(tracker_object)
        # scanner_object.scan_and_add_instruments_for_tracking()
        # Call Sacnner FRom here with instrumnet list and ktU_object
        await self.send(text_data=json.dumps({"connected": True}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def send_data(self, data):
        try:
            await self.send(text_data=json.dumps(data))
        except Exception as e:
            print("Error sending response via socket:", e)

    def _parse_query_params(self):
        query_string = self.scope['query_string'].decode('utf8')
        query_params = parse_qs(query_string)
        trading_symbols_str = query_params.get('trading_symbol', [''])[0]
        trading_symbols = [symbol for symbol in trading_symbols_str.split(',') if symbol]
        exchange = query_params.get('exchange', [''])[0]
        
        tracking_algorithm = query_params.get('tracking_algorithm', [''])[0]
        scanning_algorithm = query_params.get('scanning_algorithm', [''])[0]
        
        return {
            'trading_symbols': trading_symbols,
            'exchange': exchange,
            'scanning_algorithm': scanning_algorithm,
            'tracking_algorithm': tracking_algorithm,
        }


    async def _add_to_group_and_accept(self):
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
