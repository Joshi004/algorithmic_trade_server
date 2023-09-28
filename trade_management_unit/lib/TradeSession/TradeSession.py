import logging
import threading
from kiteconnect import KiteConnect
from django.core import serializers
import json
import asyncio
from channels.db import database_sync_to_async
from trade_management_unit.lib.common.Communicator import Communicator
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoFactory import TrackerAlgoFactory
from trade_management_unit.lib.TradeSession.TradeSessionMeta import TradeSessionMeta
from  trade_management_unit.Constants.TmuConstants import *

class TradeSession(metaclass=TradeSessionMeta):
   
    def __init__(self,user_id,scanning_algo_name,tracking_algo_name,trading_freq,kite_tick_handler,ws):
        logging.basicConfig(level=logging.DEBUG)
        self.communicator = Communicator()
        self.user_id = user_id
        self.scanning_algo_name = scanning_algo_name
        self.tracking_algo_name = tracking_algo_name
        self.trading_freq = trading_freq    
        self.communication_group = str(self)
        self.trading_freq = trading_freq
        self.kite_tick_handler = kite_tick_handler
        self.ws = ws
        self.instruments = {}
        self.token_to_symbol_map = {}
        self.scanning_algo_instance = None
        self.tracking_algo_instance = None
        self.__instanciate_scanning_algo__()
    
    def __str__(self):
        identifier =  self.user_id + "__" + self.scanning_algo_name + "__" + self.tracking_algo_name + "__" + self.trading_freq
        return identifier
    
    def __instanciate_scanning_algo__(self):
        scanning_algo_instance = ScannerAlgoFactory().get_scanner(self.scanning_algo_name,self.tracking_algo_name,self.trading_freq)
        self.scanning_algo_instance = scanning_algo_instance
        scanning_algo_instance.register_trade_session(self)
        self.kite_tick_handler.register_scanning_session(scanning_algo_instance)
        scanning_algo_instance.fetch_instrument_tokens_and_start_tracking()


    def __instanciate_tracking_algo__(self,trading_symbol):
        tracking_algo_instance = TrackerAlgoFactory(self.trading_freq,self.tracking_algo_name)
        self.tracking_algo_instance = tracking_algo_instance
        tracking_algo_instance.set_indicators(trading_symbol)
        tracking_algo_instance.register_trade_session(self)
        self.kite_tick_handler.register_tracking_session(tracking_algo_instance,trading_symbol)

    def get_formated_tick(self,tick):
        print("Format And return tick")
        return tick

    def handle_tick(self,tick):
            try:
                token = tick['instrument_token']
                symbol = self.token_to_symbol_map(token)
                last_price = tick["last_price"]
                tick_data = tick
                print("Got Tick For ",symbol,token)
                for IndicatorClass in self.tracking_algo_instance.indicators:
                    other_params = {
                        "support_price":self.instruments[symbol]["support_price"],
                        "resistance_price":self.instruments[symbol]["resistance_price"],
                        "view":self.instruments[symbol]["view"],
                        "trading_frequency":self.trading_freq,
                                    }
                    indicator_obj = IndicatorClass(str(self),symbol,other_params)
                    indicator_obj.update(last_price)
                    indicator_obj.append_information(tick_data)
                data = self.get_formated_ticks(tick)
                
            except Exception as e:
                raise("Error in on_ticks: ",e)
                return {'status':500,'message':'Something Went Wrong'}
            self.__process__instrument_actions__(data)
            self.communicator.send_data_to_channel_layer(data, self.communication_group)
        
    def initiate_trade(self,instrument):
        print ("Initiate Trade Here")

    def __process__instrument_actions__(self,instrument):
        print("Process Required Actions")
        pass

    def __add_instrument_actions__(self,instrument):
        required_action =None
        if (instrument["view"] == View.LONG):
            required_action = OrderType.BUY.value
        elif(instrument["view"] == View.SHORT):
            required_action = OrderType.SELL.value
        else:
            required_action = None
        instrument[required_action] = required_action
        return instrument
    
    def process_picked_instruments(self,instruments):
        for instrument in instruments:
            token = instrument["instrument_token"]
            symbol = instrument["trading_symbol"]
            self.token_to_symbol_map[token] = symbol
            self.kite_tick_handler.register_trade_sessions(token,self)
            self.__add_instrument_actions__(instrument)
            self.__process__instrument_actions__(instrument)
        print("Implement process_picked_instruments here",instruments)

    
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
        self.process_picked_instruments(new_instruments)
        print("Adding now")
        for instrument in new_instruments:
            self.instruments[instrument['trading_symbol']] = instrument

        # Extract instrument tokens for the WebSocket subscription
        instrument_tokens = [instrument['instrument_token'] for instrument in new_instruments]
        self.ws.subscribe(instrument_tokens)
        self.ws.set_mode(self.ws.MODE_FULL, instrument_tokens)



    def remove_tokens(self, old_instruments):
        if not isinstance(old_instruments, list):
            return

        # Filter out instruments not in self.instruments
        old_instruments = [instrument for instrument in old_instruments if instrument['trading_symbol'] in self.instruments]

        if not old_instruments:
            print("No old instruments to remove")
            return

        # Remove old instruments from self.instruments
        for instrument in old_instruments:
            self.instruments.pop(instrument['trading_symbol'], None)

        # Extract instrument tokens for the WebSocket unsubscription
        instrument_tokens = [instrument['instrument_token'] for instrument in old_instruments]

        self.ws.unsubscribe(instrument_tokens)




            
