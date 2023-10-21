import logging
import threading
from kiteconnect import KiteConnect
from django.core import serializers
import json
import asyncio
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from trade_management_unit.lib.common.Communicator import Communicator
from trade_management_unit.models.TradeSession import TradeSession as TradeSessionDB
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoFactory import TrackerAlgoFactory
from trade_management_unit.lib.TradeSession.TradeSessionMeta import TradeSessionMeta
from  trade_management_unit.Constants.TmuConstants import *
from  trade_management_unit.models.Trade import Trade
from  trade_management_unit.models.Order import Order
from  trade_management_unit.lib.TradeSession.RiskManager import RiskManager
from  trade_management_unit.lib.Portfolio.Portfolio import Portfolio


import concurrent.futures
from datetime import datetime

class TradeSession(metaclass=TradeSessionMeta):
   
    def __init__(self,user_id,scanning_algo_name,tracking_algo_name,trading_freq,kite_tick_handler,ws,dummy):
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
        self.dummy = dummy
        self.__instanciate_tracking_algo__()
        self.__instanciate_scanning_algo__()
        self.trade_session_id = self.get_trade_session_id()
    
    def __str__(self):
        identifier =  self.user_id + "__" + self.scanning_algo_name + "__" + self.tracking_algo_name + "__" + self.trading_freq
        return identifier

    def get_trade_session_id(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(database_sync_to_async(self.fetch_or_create_trade_session))
            result = future.result()
        self.scanning_algo_instance.scan_and_add_instruments_for_tracking(result)
    

    def fetch_or_create_trade_session(self):
            scanning_algo_name = self.scanning_algo_name
            tracking_algo_name = self.tracking_algo_name
            trading_freq = self.trading_freq
            dummy = self.dummy
            user_id = self.user_id

            try:
                trade_session = TradeSessionDB.objects.get(
                    user_id=user_id,
                    scanning_algorithm__name=scanning_algo_name,
                    tracking_algorithm__name=tracking_algo_name,
                    trading_frequency=trading_freq
                )
            except TradeSessionDB.DoesNotExist:
                # If no matching trade session is found, create a new one
                trade_session = TradeSessionDB(
                    user_id=user_id,
                    scanning_algorithm__name=scanning_algo_name,
                    tracking_algorithm__name=tracking_algo_name,
                    trading_frequency=trading_freq,
                    is_active=True,  # Set is_active to True
                    started_at=datetime.now(),  # Set started_at to current timestamp
                    closed_at=None,  # Set closed_at to None
                    dummy=dummy  # Set dummy based on the parameter
                )
                trade_session.save()  # Save the new trade session to the database


            return trade_session.id


        
    
    def __instanciate_scanning_algo__(self):
        scanning_algo_instance = ScannerAlgoFactory().get_scanner(self.scanning_algo_name,self.tracking_algo_name,self.trading_freq)
        self.scanning_algo_instance = scanning_algo_instance
        scanning_algo_instance.register_trade_session(self)
        self.kite_tick_handler.register_scanning_session(scanning_algo_instance)
        scanning_algo_instance.fetch_instrument_tokens_and_start_tracking()


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
                "last_price" : tick["last_price"],
                "last_quantity" : tick["last_quantity"],
                "average_price" : tick["average_price"],
                "volume" : tick["volume"],
                "buy_quantity" : tick["buy_quantity"],
                "sell_quantity" : tick["sell_quantity"],
            }
        }
        instrument_obj["required_action"] = self.tracking_algo_instance.get_required_action(instrument_obj)
        return instrument_obj

    def async_tick_handler(self,tick):
        try:
            token = tick['instrument_token']
            symbol = self.token_to_symbol_map[token]
            last_price = tick["last_price"]
            print("Got Tick For ",symbol,token)
            for IndicatorClass in self.tracking_algo_instance.indicators:
                other_params = {
                    "support_price":self.instruments[symbol]["support_price"],
                    "resistance_price":self.instruments[symbol]["resistance_price"],
                    "view":self.instruments[symbol]["view"],
                                }
                indicator_obj = IndicatorClass(str(self),symbol,self.trading_freq,other_params)
                indicator_obj.update(last_price)
                indicator_obj.append_information(tick)
            data = self.get_formated_tick(tick,symbol)
            
        except Exception as e:
            raise("Error in on_ticks: ",e)
            # return {'status':500,'message':'Something Went Wrong'}
        self.__process__instrument_actions__(data)
        self.communicator.send_data_to_channel_layer(data, self.communication_group)
        


    def handle_tick(self,tick):
        tick_handler_thread = threading.Thread(target=self.async_tick_handler,args=(tick,))
        tick_handler_thread.setDaemon(True)
        tick_handler_thread.start()
            

    def __process__instrument_actions__(self,instrument):
        trading_symbol = instrument["trading_symbol"]
        action = instrument["required_action"]
        if action:
            market_price = instrument["market_price"]
            trade_id = Trade.fetch_or_initiate_trade(trading_symbol, action, self.trade_session_id, self.user_id, self.dummy)
            risk_manager = RiskManager()
            # !!!! Change implementtaion of teh following
            print("!!! Change Implimentation here !!!!")
            quantity,frictional_losses = risk_manager.get_quantity_and_frictional_losses(action,market_price,instrument["support_price"],instrument["resistance_price"],self.user_id)
            print("!!! Order from Zerodha",trading_symbol,action)
            kite_order_id = self.place_order_on_kite(trading_symbol,quantity,action,instrument["support_price"],instrument["resistance_price"],instrument["market_price"])
            order_id = Order.initiate_order( action, instrument["id"], trade_id, self.dummy, kite_order_id, frictional_losses, self.user_id, qunatity)
            return trade_id
        return None


    def place_order_on_kite(self,trading_symbol,qunatity,action,support_price,resistance_price,market_price):
        stoploss = market_price - 0.99*support_price if action == OrderType.BUY else  - 1.01*support_price - market_price
        squareoff = 1.01*resistance_price - market_price if action == OrderType.BUY else market_price - 0.99*support_price
        if (not self.dummy):   
            params = {"trading_symbol":trading_symbol,
                      "qunatity":qunatity,
                      "order_type":action,
                      "product":"BO",
                      "squareoff":squareoff,
                      "stoploss":stoploss,
                      "validity":"IOC",
                      "price":market_price
                      }
            resposne  = Portfolio().place_order(params)
            return resposne.trade_id
        else:
            return self.user_id+"__"+str(datetime.now)


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

            trade_id = self.__process__instrument_actions__(instrument)
            
            self.instruments[instrument['trading_symbol']] = instrument
            self.token_to_symbol_map[token] = symbol
            self.kite_tick_handler.register_trade_sessions(token,self)

        # Extract instrument tokens for the WebSocket subscription
        instrument_tokens = [instrument['instrument_token'] for instrument in new_instruments]
        self.ws.subscribe(instrument_tokens)
        # self.ws.set_mode(self.ws.MODE_LTP, instrument_tokens)



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




            
