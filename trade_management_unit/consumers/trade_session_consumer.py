import json
from datetime import datetime
from django.db.models import Q
from urllib.parse import parse_qs
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from trade_management_unit.models.Instrument import Instrument
from trade_management_unit.lib.Algorithms.AlgoFactory import AlgoFactory
from trade_management_unit.lib.Kite.KiteTickerUser import KiteTickerUser

class TradeSessionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        query_params = self._parse_query_params()
        trading_symbols = query_params.get('trading_symbols', [])
        exchange = query_params.get('exchange', '')
        algorithm_name = query_params.get('algorithm', '')

        self.room_group_name = self._generate_room_group_name(trading_symbols)
        instrument_tokens, error_message = await self._get_validated_instrument_tokens(trading_symbols, exchange)
        if error_message:
            await self.close()
            print({"error": error_message})

        await self._add_to_group_and_accept()
        ktu_object = KiteTickerUser(instrument_tokens, self.room_group_name)
        kt_object = ktu_object.get_kite_ticker_instance()
        algorithm_object = AlgoFactory().get_instance(algorithm_name)
        algorithm_object.set_algorithm(ktu_object)
        kt_object.connect()
        await self.send(text_data=json.dumps({"connected": True}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def send_data(self, event):
        try:
            await self.send(text_data=json.dumps(event["data"]))
        except Exception as e:
            print("Error sending response via socket:", e)

    def _parse_query_params(self):
        query_string = self.scope['query_string'].decode('utf8')
        query_params = parse_qs(query_string)
        trading_symbols_str = query_params.get('trading_symbol', [''])[0]
        trading_symbols = [symbol for symbol in trading_symbols_str.split(',') if symbol]
        exchange = query_params.get('exchange', [''])[0]
        algorithm_name = query_params.get('algorithm', [''])[0]
        
        return {
            'trading_symbols': trading_symbols,
            'exchange': exchange,
            'algorithm': algorithm_name,
        }

    @database_sync_to_async
    def _get_instrument_tokens(self, trading_symbols, exchange):
        instrument_tokens = []
        
        for symbol in trading_symbols:
            try:
                instruments = Instrument.objects.filter(
                    Q(trading_symbol__iexact=symbol) & Q(exchange__iexact=exchange)
                )
                unique_tokens = set(instrument.instrument_token for instrument in instruments)
                
                if len(unique_tokens) > 1:
                    return (None, f"Multiple instrument tokens found for trading symbol: {symbol} and exchange: {exchange}")
                
                instrument_tokens.append(unique_tokens.pop())
            except Instrument.DoesNotExist:
                return (None, f"Invalid trading symbol: {symbol} or exchange: {exchange}")
        
        return (instrument_tokens, None)

    async def _get_validated_instrument_tokens(self, trading_symbols, exchange):
        instrument_tokens, error_message = await self._get_instrument_tokens(trading_symbols, exchange)
        
        if error_message:
            return (None, error_message)
        
        return (instrument_tokens, None)

    def _generate_room_group_name(self, trading_symbols):
       timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
       return f"{timestamp}_{'-'.join(trading_symbols)}"

    async def _add_to_group_and_accept(self):
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
