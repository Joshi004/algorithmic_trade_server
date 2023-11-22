import logging
import threading
from trade_management_unit.lib.common.Communicator import Communicator
from trade_management_unit.models.TradeSession import TradeSession as TradeSessionDB
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoFactory import TrackerAlgoFactory
from trade_management_unit.lib.TradeSession.TradeSessionMeta import TradeSessionMeta
from  trade_management_unit.Constants.TmuConstants import *
from  trade_management_unit.models.Trade import Trade
from  trade_management_unit.models.Algorithm import Algorithm
from django.db import connections
from trade_management_unit.lib.common.Utils import *
from trade_management_unit.lib.Kite.KiteTickhandler import KiteTickhandler
import pytz

import concurrent.futures


class TradeSession(metaclass=TradeSessionMeta):
   
    def __init__(self,user_id,scanning_algo_name,tracking_algo_name,trading_freq,dummy,kite_tick_handler,ws):
        logging.basicConfig(level=logging.DEBUG)
        self.communicator = Communicator()
        self.user_id = user_id
        self.scanning_algo_name = scanning_algo_name
        self.tracking_algo_name = tracking_algo_name
        self.trading_freq = trading_freq
        self.dummy = dummy
        self.trading_freq = trading_freq
        self.kite_tick_handler = kite_tick_handler
        self.ws = ws
        self.instruments = {}
        self.token_to_symbol_map = {}
        self.scanning_algo_instance = None
        self.tracking_algo_instance = None

        self.trade_session_id =  self.get_trade_session_id()
        self.communication_group = str(self)
        self.__instanciate_tracking_algo__()
        self.__instanciate_scanning_algo__()
        self.track_active_trade_instruments()
    
    def __str__(self):
        identifier = "trade_session__"+str(self.trade_session_id)
        return identifier
    def __eq__(self, other):
        if isinstance(other, TradeSession):
            return self.id == other.id
        return False


    def get_trade_session_id(self):
        scanning_algo_id = Algorithm.get_id_by_name(self.scanning_algo_name)
        tracking_algo_id = Algorithm.get_id_by_name(self.tracking_algo_name)
        trade_session = TradeSessionDB.fetch_active_trade_session(self.user_id, scanning_algo_id, tracking_algo_id, self.trading_freq, self.dummy)
        if (not trade_session):
            trade_session = TradeSessionDB.create_trade_session(self.user_id, scanning_algo_id, tracking_algo_id, self.trading_freq, self.dummy)
        return trade_session.id

    @classmethod
    def check_if_session_exists(cls, user_id, scanning_algo_name, tracking_algo_name, trading_freq, dummy):
        unique_class_identifier = str(dummy) + "__" + user_id + "__" + scanning_algo_name + "__" + tracking_algo_name + "__" + trading_freq
        return unique_class_identifier in cls._instances


    def track_active_trade_instruments(self):
        active_trades = Trade.objects.select_related('instrument').filter(trade_session_id=self.trade_session_id, is_active=True)
        instrument_objects = []
        for trade in active_trades:
            instrument = trade.instrument
            instrument_object = {
                'instrument_id': instrument.id,
                'instrument_token': instrument.id,
                'trading_symbol': instrument.trading_symbol,
                'trading_frequency': self.trading_freq,
                'required_action': None
            }
            instrument_objects.append(instrument_object)
            self.add_tokens([instrument_object])
            # self.token_to_symbol_map[instrument.id] = instrument.trading_symbol
            # self.kite_tick_handler.register_trade_sessions(instrument.id, self)
            # self.ws.subscribe([instrument.id])

            # {'instrument_id': 7436801,
            #  'trading_symbol': 'ZUARI',
            #  'instrument_token': 7436801,
            #  'trade_freqency': '10minute',
            #  'effective_trend': <Trends.UPTREND:
            # 'uptrend'>, 'support_price': 155.0,
            # 'resistance_price': 155.5,
            # 'support_strength': 7.620394614514719e-06,
            # 'resistance_strength': 0.006657176735240058,
            # 'movement_potential': 0.5760000000000001,
            # 'market_data': {'volume': 64022,
            #                 'market_price': 155.15,
            #                 'last_quantity': 196},
            #                 'required_action': 'buy'}

        return {"data": {"existing_instruments": instrument_objects}, "meta": {"size": len(instrument_objects)}}




        
    
    def __instanciate_scanning_algo__(self):
        scanning_algo_instance = ScannerAlgoFactory().get_scanner(self.scanning_algo_name,self.tracking_algo_name,self.trading_freq)
        self.scanning_algo_instance = scanning_algo_instance
        scanning_algo_instance.register_trade_session(self)
        # self.kite_tick_handler.register_scanning_session(scanning_algo_instance)
        scanning_algo_instance.fetch_instrument_tokens_and_start_tracking(self.user_id,self.dummy)


    def __instanciate_tracking_algo__(self):
        tracking_algo_instance = TrackerAlgoFactory().get_instance(self.tracking_algo_name,self.trading_freq,self.scanning_algo_name)
        self.tracking_algo_instance = tracking_algo_instance
        tracking_algo_instance.set_indicators()
        tracking_algo_instance.register_trade_session(self)
        print("!!! Enable register_tracking_session if needed !!! ")
        # self.kite_tick_handler.register_tracking_session(tracking_algo_instance,trading_symbol)



    def get_formated_tick(self,tick,symbol):
        instrument_obj = {
            "trading_symbol" : self.instruments[symbol]["trading_symbol"],
            "instrument_token" : self.instruments[symbol]["instrument_token"],
            "trade_freqency" : self.instruments[symbol]["trade_freqency"],
            "indicator_data" : tick["indicator_data"],
            "market_data" : {
                "market_price" : tick["last_price"],
                "last_quantity" : tick["last_quantity"],
                "volume" : tick["volume"],
            }
        }
        instrument_obj["required_action"] = self.tracking_algo_instance.get_required_action(instrument_obj)
        return instrument_obj

    def tick_handler(self,tick):
        try:
            token = tick['instrument_token']
            symbol = self.token_to_symbol_map[token]
            last_price = tick["last_price"]
            trade = Trade.fetch_active_trade(token,self.trade_session_id,self.user_id,self.dummy)
            if(not trade):
                print(symbol,"Not Added To Trades yet")
                self.close_connections()
                return

            trade_id = trade.id
            print("Got Tick For ",symbol,token,self.instruments[symbol])
            if(not trade.max_price or last_price > trade.max_price):
                trade.max_price = last_price
                trade.save()
            elif(not trade.min_price or last_price < trade.min_price):
                trade.min_price = last_price
                trade.save()

            for IndicatorClass in self.tracking_algo_instance.indicators:
                indicator_obj = IndicatorClass(self.trade_session_id,symbol,self.trading_freq,trade_id,token)
                indicator_obj.update(last_price)
                indicator_obj.append_information(tick)
                # !!!!! Make Sure Every Indicator object is garbage collected ones the trade is terminated fro the symbol
                if(indicator_obj.price_zone_changed):
                    indicator_obj.mark_into_indicator_records(tick,self.trade_session_id,self.user_id,self.dummy,self.scanning_algo_name)

            formated_instrument_data = self.get_formated_tick(tick,symbol)
            if(formated_instrument_data["required_action"]):
                trade,order = self.tracking_algo_instance.process_tracker_actions(formated_instrument_data,self.trade_session_id,self.user_id,self.dummy)
                if(not trade.is_active):
                    self.remove_tokens([token])
                    communication_bit = {
                    "event_type": COMMUNICATION_ACTION.TERMINATE_TRADE.value,
                    "order_action": order.order_type,
                    "order_quantity": order.quantity,
                    "trade_session_id": self.trade_session_id,
                    "trading_symbol": symbol,
                    "instrument_id": int(token),
                    "price": float(order.price),
                    "net_profit": float(trade.net_profit if trade.net_profit else 0),
                    "timestamp": current_ist()
                }
                self.communicator.send_data_to_channel_layer(communication_bit, self.communication_group)
        except Exception as e:
            self.close_connections()
            raise("Error in on_ticks: ",e)

        self.close_connections()
        # self.communicator.send_data_to_channel_layer(formated_instrument_data, self.communication_group)
        
    def close_connections(self):
        for conn in connections.all():
            conn.close()

    def handle_tick(self,tick):
        self.tick_handler(tick)
        # tick_handler_thread = threading.Thread(target=self.async_tick_handler,args=(tick,))
        # tick_handler_thread.setDaemon(True)
        # tick_handler_thread.start()


    def __add_instrument_actions__(self,instrument):
        print("Check Volume COnstraints and also min ratio if needed ")
        required_action =None
        if (instrument["view"] == View.LONG):
            required_action = OrderType.BUY.value
        elif(instrument["view"] == View.SHORT):
            required_action = OrderType.SELL.value
        else:
            required_action = None
        instrument["required_action"] = required_action
        return instrument
    
    
    def add_tokens(self, new_instruments):
        if not isinstance(new_instruments, list):
            print("Error: new_instruments must be a list of instrument tokens")
            return

        # Filter out instruments already in self.instruments
        new_instruments = [instrument for instrument in new_instruments if instrument['trading_symbol'] not in self.instruments]

        if not new_instruments:
            print("no new instruments to add")
            return
        # Add new instruments to self.instruments
        print("Adding now")
        for instrument in new_instruments:
            token = instrument["instrument_token"]
            symbol = instrument["trading_symbol"]

            trade, order = self.scanning_algo_instance.process_scanner_actions(instrument,self.user_id,self.dummy,self.trade_session_id)
            trade_id = trade.id if trade else None
            self.token_to_symbol_map[token] = symbol
            if(trade_id):
                self.scanning_algo_instance.mark_into_scan_records(trade_id,self.tracking_algo_name,instrument)
                self.instruments[instrument['trading_symbol']] = instrument
                self.kite_tick_handler.register_trade_sessions(token,self)
                try:
                    self.ws.subscribe([token])
                except:
                    print(" !!!!!!!! Error Subscribing  retrying !!!!!!!")
                    kite_tick_handler = KiteTickhandler()
                    self.ws = kite_tick_handler.get_kite_ticker_instance()
                    self.ws.connect(threaded=True)
                    self.ws.subscribe([token])


                communication_bit = {
                    "event_type": COMMUNICATION_ACTION.INITIATE_TRADE.value,
                    "order_action": order.order_type if order else None,
                    "order_quantity": order.quantity if order else None,
                    "trade_session_id": self.trade_session_id,
                    "trading_symbol": symbol,
                    "instrument_id": int(token),
                    "price": float(instrument["market_data"]["market_price"]),
                    "net_profit": float(trade.net_profit if trade.net_profit else 0),
                    "timestamp": current_ist()
                }
                self.communicator.send_data_to_channel_layer(communication_bit, self.communication_group)

        # Extract instrument tokens for the WebSocket subscription
        # instrument_tokens = [instrument['instrument_token'] for instrument in new_instruments]

        # self.ws.set_mode(self.ws.MODE_LTP, instrument_tokens)


    def remove_tokens(self, tokens_to_remove):
        if not isinstance(tokens_to_remove, list):
            return

        # Filter out instruments not in self.instruments
        old_instruments  = []
        for token in tokens_to_remove:
            symbol = self.token_to_symbol_map[token]
            if symbol in self.instruments:
                 old_instruments.append({
                     "instrument_token" : token,
                     "trading_symbol" : symbol
                 })


        if not old_instruments:
            print("No old instruments to remove")
            return


        # Extract instrument tokens for the WebSocket unsubscription
        instrument_tokens = [instrument['instrument_token'] for instrument in old_instruments]
        self.ws.unsubscribe(instrument_tokens)
        print("!!!! Remove all candle Chart and singlton onjects as well")
        # Remove old instruments from self.instruments
        for instrument in old_instruments:
            self.instruments.pop(instrument['trading_symbol'], None)





            
