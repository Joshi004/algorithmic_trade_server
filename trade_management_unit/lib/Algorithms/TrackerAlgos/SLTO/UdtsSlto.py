from trade_management_unit.lib.Indicators.SLTO.SLTO import SLTO
from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoMeta import TrackerAlgoMeta
class UdtsSlto(metaclass=TrackerAlgoMeta):
    def __init__(self,trading_frequency,scanning_algorithm_name):
        self.trading_frequency = trading_frequency
        self.scanning_algorithm_name = scanning_algorithm_name
        self.indicators = []
        self.trade_sessions = {}
    
    def __str__(self):
        identifier = self.trading_frequency+"__"+self.scanning_algorithm_name
        return identifier

    def set_indicators(self):
        self.indicators.append(SLTO)
    
    def get_required_action(self,instrument_obj):
        return instrument_obj["indicator_data"]["slto"]["required_action"]

    
    def register_trade_session(self,trade_session_obj):
        self.trade_sessions[str(trade_session_obj)] = trade_session_obj