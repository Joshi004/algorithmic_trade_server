from trade_management_unit.lib.Indicators.SLTO.SLTO import SLTO
from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoMeta import TrackerAlgoMeta
from trade_management_unit.models import Trade
from trade_management_unit.models.Order import  Order
from trade_management_unit.lib.Portfolio.Portfolio import Portfolio
from trade_management_unit.Constants.TmuConstants import  *
from trade_management_unit.lib.TradeSession.RiskManager import RiskManager
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


    def process_tracker_actions(self,instrument,trade_session_id,user_id,dummy):
        trading_symbol = instrument["trading_symbol"]
        action = instrument["required_action"]
        if action:
            instrument_id = instrument["instrument_id"]
            market_price = instrument["market_data"]["market_price"]
            trade_id = Trade.fetch_active_trade(instrument_id,trade_session_id,user_id,dummy).id
            quantity = self.__get_square_off_quantity__(instrument_id,trade_session_id,user_id,trade_id,dummy)
            if not dummy:
                order_params = {"trading_symbol":trading_symbol,
                                "exchange": DEFAULT_EXCHANGE,
                                "transaction_type": action,
                                "order_type": "MARKET",
                                "quantity":quantity,
                                "product": "MIS",
                                "validity": "DAY"}
                kite_order_id = Portfolio.initiate_order(order_params)

            frictional_losses = RiskManager().get_frictional_losses(TRADE_TYPE["intraday"],market_price, quantity, action == "BUY")
            order = Order.initiate_order(action, instrument_id, trade_id, dummy, kite_order_id, frictional_losses, user_id, quantity)
            return trade_id
        return None

    def __get_square_off_quantity__(self,instrument_id,trade_session_id,user_id,trade_id,dummy):
        order = Order.fetch_order(instrument_id, trade_id,dummy,user_id)
        existing_quantity = order.quantity
        return existing_quantity

