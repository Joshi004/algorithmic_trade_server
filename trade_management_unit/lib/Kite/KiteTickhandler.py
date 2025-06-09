from kiteconnect import KiteTicker
import threading
from trade_management_unit.lib.common.Utils.custome_logger import log
from django.db import connections
from trade_management_unit.lib.common.Utils.Utils import *
import requests
from django.conf import settings

class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class KiteTickhandler(metaclass=SingletonMeta):
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.integration_service_url = getattr(settings, 'INTEGRATION_SERVICE_URL', 'http://localhost:8000/integration')
        self.api_key = None
        self.api_secret = None
        self.access_token = None
        self.kto = None
        self.scanning_sessions = {}
        self.tracking_sessions = {}
        self.trade_sessions = {}
        
        if user_id:
            self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from integration service"""
        try:
            # For now, we'll need to make an API call to get credentials
            # This is a simplified approach - in production, you might want to cache these
            # or have a more efficient way to get credentials
            
            # Note: This is a placeholder - you'll need to implement an endpoint 
            # in integration service to get credentials for a user
            # For now, we'll use a fallback approach
            
            # You might want to add an endpoint like /get_user_credentials/ in integration service
            # that returns the api_key, api_secret, and access_token for a user
            
            log("Loading credentials from integration service...")
            # Placeholder - implement actual credential loading logic
            
        except Exception as e:
            log(f"Error loading credentials: {str(e)}", "error")
    
    def set_credentials(self, api_key, api_secret, access_token):
        """Manually set credentials - useful for initialization"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
    
    def register_trade_sessions(self, token, trade_session):
        if token in self.trade_sessions:
            self.trade_sessions[token].append(trade_session)
        else:
            self.trade_sessions[token] = [trade_session]

    def unregister_trade_session(self, tokens, trade_session):
        for token in tokens:
            if token in self.trade_sessions:
                if trade_session in self.trade_sessions[token]:
                    self.trade_sessions[token].remove(trade_session)
                    if not self.trade_sessions[token]:
                        del self.trade_sessions[token]

    def set_tracker_session(self, identifier, tracker_session):
        self.tracker_sessions[identifier] = tracker_session

    def async_tick_handler(self, ticks):
        log(f"Got Tick Lot {str(ticks)}")
        for tick in ticks:
            token = tick['instrument_token']
            if token in self.trade_sessions:
                for trade_session in self.trade_sessions[token]:
                    trade_session.handle_tick(tick)
        self.close_connections()

    def close_connections(self):
        for conn in connections.all():
            conn.close()

    def on_ticks(self, ws, ticks):
        tick_handler_thread = threading.Thread(target=self.async_tick_handler, args=(ticks,), name="tick_handler")
        tick_handler_thread.setDaemon(True)
        tick_handler_thread.start()

    def register_tracking_session(self, tracking_session, trading_symbol):
        trading_frequency = tracking_session.trading_frequency
        identifier = str(tracking_session)
        self.tracking_sessions[trading_symbol] = self.tracking_sessions.get(trading_symbol) or {}
        self.tracking_sessions[trading_symbol][trading_frequency] = self.tracking_sessions[trading_symbol].get(trading_frequency) or {}
        self.tracking_sessions[trading_symbol][trading_frequency][identifier] = tracking_session

    def on_connect(self, ws, response):
        log("Connected and ready to subscribe instruments")
        self.ws = ws

    def on_error(self, ws, code, reason):
        # Callback to receive live websocket errors.
        log(f"Error On WS Connection : {str(reason)}", "error")

    def get_kite_ticker_instance(self):
        if self.kto:
            return self.kto
        else:
            if not self.access_token:
                log("No access token available for KiteTicker", "error")
                return None
                
            kto = KiteTicker(self.api_key, self.access_token)
            kto.on_connect = self.on_connect
            kto.on_ticks = self.on_ticks
            kto.on_close = self.on_close
            kto.on_error = self.on_error
            self.kto = kto
            return self.kto

    def on_close(self, ws, code, reason):
        ws.stop()
