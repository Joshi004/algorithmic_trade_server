from kiteconnect import KiteTicker
from trade_management_unit.lib.common.EnvFile import EnvFile

class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]    


class KiteTickhandler(metaclass=SingletonMeta):
    def __init__(self):
        self.env = EnvFile('.env')
        self.api_key = self.env.read("api_key")
        self.api_secret = self.env.read("api_secret")
        self.access_token = self.env.read("access_token")
        self.kto = None
        self.scanning_sessions = {}
        self.tracking_sessions = {}
        self.trade_sessions = {}
    
    def register_trade_sessions(self,token,trade_sesion):
        if token in self.trade_sessions:
            self.trade_sessions[token].append(trade_sesion)
        else:
            self.trade_sessions[token] = [trade_sesion]


    def set_tracker_session(self,identifier,tracker_session):
        self.tracker_sessions[identifier] = tracker_session
    



    def on_ticks(self,ws,ticks):
        for tick in ticks:
            token = tick['instrument_token']
            for trade_session in self.trade_sessions[token]:
                trade_session.handle_tick(tick)
                

    
    # def register_scanning_session(self,sacnning_session):
    #     frequency = sacnning_session.trade_freqency
    #     identifier = str(sacnning_session)
    #     self.scanning_sessions[frequency] = self.scanning_sessions.get(frequency) or {}
    #     self.scanning_sessions[frequency][identifier] = sacnning_session


    def register_tracking_session(self,tracking_session,trading_symbol):
        trading_frequency = tracking_session.trading_frequency
        identifier = str(tracking_session)
        self.tracking_sessions[trading_symbol] = self.tracking_sessions.get(trading_symbol) or {}
        self.tracking_sessions[trading_symbol][trading_frequency] = self.tracking_sessions[trading_symbol].get(trading_frequency) or {}
        self.tracking_sessions[trading_symbol][trading_frequency][identifier] = tracking_session
        pass

    def on_connect(self,ws,response):
        print("Connected--------")     
        self.ws = ws
        # scanning_algo_name = self.communication_group.split("-")[0]
        # tracking_algo_name = self.communication_group.split("-")[1]
        # scanner_object = ScannerAlgoFactory().get_scanner(scanning_algo_name,tracking_algo_name,self.trading_freq)
        # class_identifier = str(self)
        # if(class_identifier not in scanner_object.tracker_sessions):
        #     scanner_object.set_tracker_session(class_identifier,self)        
        #     self.fetch_instruments_and_send_to_scanner(scanner_object)
        # else:
        #     print("Not Creating Another Scanner Object as one is already runig")


    def get_kite_ticker_instance(self):
        if(self.kto):
            return self.kto
        else:
            kto = KiteTicker(self.api_key,self.access_token)
            kto.on_connect = self.on_connect
            kto.on_ticks = self.on_ticks
            kto.on_close = self.on_close
            self.kto = kto
            return self.kto


    def on_close(self,ws,code,reason):
        ws.stop()
