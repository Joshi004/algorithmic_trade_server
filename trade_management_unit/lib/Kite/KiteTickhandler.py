from kiteconnect import KiteTicker
import threading
from trade_management_unit.lib.common.Utils.custome_logger import log
from django.db import connections
from trade_management_unit.lib.common.Utils.Utils import *
from trade_management_unit.models.UserConfiguration import UserConfiguration

class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]    


class KiteTickhandler(metaclass=SingletonMeta):
    def __init__(self, user_id=1):  # Default user_id as 1 for backward compatibility
        self.user_id = user_id
        
        # Get credentials from database
        self.api_key = UserConfiguration.get_attribute(user_id, 'api_key')
        self.api_secret = UserConfiguration.get_attribute(user_id, 'api_secret')
        self.access_token = UserConfiguration.get_attribute(user_id, 'access_token')
        
        if not self.api_key or not self.api_secret or not self.access_token:
            log(f"API credentials not found for user_id {user_id}. Make sure they are set in the database.", "error")
        
        self.kto = None
        self.scanning_sessions = {}
        self.tracking_sessions = {}
        self.trade_sessions = {}
    
    def register_trade_sessions(self,token,trade_sesion):
        if token in self.trade_sessions:
            self.trade_sessions[token].append(trade_sesion)
        else:
            self.trade_sessions[token] = [trade_sesion]

    def unregister_trade_session(self, tokens, trade_sesion):
        for token in tokens:
            if token in self.trade_sessions:
                if trade_sesion in self.trade_sessions[token]:
                    self.trade_sessions[token].remove(trade_sesion)
                    if not self.trade_sessions[token]:
                        del self.trade_sessions[token]

    def set_tracker_session(self,identifier,tracker_session):
        self.tracker_sessions[identifier] = tracker_session
    
    def async_tick_handler(self,ticks):
        log(f"Got Tock Lot {str(ticks)}")
        for tick in ticks:
            token = tick['instrument_token']
            for trade_session in self.trade_sessions[token]:
                trade_session.handle_tick(tick)
        self.close_connections()

    def close_connections(self):
        for conn in connections.all():
            conn.close()

    def on_ticks(self,ws,ticks):
        tick_handler_thread = threading.Thread(target=self.async_tick_handler,args=(ticks,),name="tick_handler")
        tick_handler_thread.setDaemon(True)
        tick_handler_thread.start()

    def register_tracking_session(self,tracking_session,trading_symbol):
        trading_frequency = tracking_session.trading_frequency
        identifier = str(tracking_session)
        self.tracking_sessions[trading_symbol] = self.tracking_sessions.get(trading_symbol) or {}
        self.tracking_sessions[trading_symbol][trading_frequency] = self.tracking_sessions[trading_symbol].get(trading_frequency) or {}
        self.tracking_sessions[trading_symbol][trading_frequency][identifier] = tracking_session

    def on_connect(self,ws,response):
        log("Connected and ready to subscribe instruments")
        self.ws = ws

    def on_error(ws, code, reason):
        # Callback to receive live websocket errors.
        log(f"Error On WS Connection : {str(reason)}","error")

    def get_kite_ticker_instance(self):
        if(self.kto):
            return self.kto
        else:
            # Get fresh credentials in case they've been updated
            self.access_token = UserConfiguration.get_attribute(self.user_id, 'access_token')
            
            if not self.api_key or not self.access_token:
                log("Missing API credentials - cannot initialize KiteTicker instance", "error")
                return None
                
            kto = KiteTicker(self.api_key, self.access_token)
            kto.on_connect = self.on_connect
            kto.on_ticks = self.on_ticks
            kto.on_close = self.on_close
            kto.on_error = self.on_error
            self.kto = kto
            return self.kto

    def on_close(self,ws,code,reason):
        ws.stop()
