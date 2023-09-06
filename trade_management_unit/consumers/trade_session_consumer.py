from channels.generic.websocket import WebsocketConsumer,AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from urllib.parse import parse_qs
import json
from trade_management_unit.lib.Kite.KiteTickerUser import KiteTickerUser
from channels.db import database_sync_to_async
from trade_management_unit.models.Instrument import Instrument
from datetime import datetime
from django.db.models import Q
from trade_management_unit.lib.Algorithms.AlgoFactory import AlgoFactory

class TradeSession(AsyncWebsocketConsumer):
    @database_sync_to_async
    def get_instrument_tokens(self, trading_symbols, exchange):
        # Get the instrument tokens for the specified trading symbols and exchange
        instrument_tokens = []
        for symbol in trading_symbols:
            try:
                instruments = Instrument.objects.filter(Q(trading_symbol__iexact=symbol) & Q(exchange__iexact=exchange))
                unique_tokens = set(instrument.instrument_token for instrument in instruments)
                if len(unique_tokens) > 1:
                    return (None, "Multiple instrument tokens found for trading symbol: {} and exchange: {}".format(symbol, exchange))
                instrument_tokens.append(unique_tokens.pop())
            except Instrument.DoesNotExist:
                return (None, "Invalid trading symbol: {} or exchange: {}".format(symbol, exchange))
        return (instrument_tokens, None)

    async def get_validated_instrument_tokens(self, trading_symbols, exchange):
        # Get the instrument tokens for the specified trading symbols and exchange
        instrument_tokens, error_message = await self.get_instrument_tokens(trading_symbols, exchange)
        if error_message:
            return (None, error_message)
        return (instrument_tokens, None)
    
    
    def generate_room_group_name(self, trading_symbols):
        print("generating Group name from",trading_symbols)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        return ( str(timestamp) + "_"+'-'.join(trading_symbols))
    
    async def connect(self):
        print("In Consumer Now")
        query_params = parse_qs(self.scope['query_string'].decode('utf8'))
        trading_symbols_str = query_params.get('trading_symbol', [''])[0]
        trading_symbols = [symbol for symbol in trading_symbols_str.split(',') if symbol]
        exchange = query_params.get('exchange', [''])[0]
        algorithm_name = query_params.get('algorithm', [''])[0]
        self.room_group_name = self.generate_room_group_name(trading_symbols)
        instrument_tokens, error_message = await self.get_validated_instrument_tokens(trading_symbols, exchange)
        if error_message:
            # await self.send(text_data=json.dumps({"error": error_message}))
            await self.close()
            print( {"error": error_message})
        
        print("Group Name",self.room_group_name)
        algorithm_object = AlgoFactory().get_instance(algorithm_name)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        ktu_obect = KiteTickerUser(instrument_tokens,self.room_group_name)    
        kt_object = ktu_obect.get_instance()
        algorithm_object.set_alogorithm(ktu_obect)
        kt_object.connect()
        await self.send(text_data=json.dumps({"connected":True}))



    async def disconnect(self, close_code):
        print("Disconnected Now")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        # raise channels.exceptions.StopConsumer()



    async def receive(self, text_data=None, bytes_data=None):
        print("Data Recieverd")
        pass


    async def send_data(self, event):
        try:
            # print("in Send Data Send event for ticker",event)
            await self.send(text_data=json.dumps(event["data"]))
        except Exception as e:
            print ("error Sending reposnse via socket".e)

