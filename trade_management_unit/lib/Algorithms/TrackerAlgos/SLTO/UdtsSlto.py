from trade_management_unit.lib.Indicators.SLTO.SLTO import SLTO
from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoMeta import TrackerAlgoMeta
from trade_management_unit.models.Trade import Trade
from trade_management_unit.models.Order import  Order
from trade_management_unit.lib.Portfolio.Portfolio import Portfolio
from trade_management_unit.Constants.TmuConstants import  *
from trade_management_unit.models.DummyAccount import DummyAccount
from trade_management_unit.lib.TradeSession.RiskManager import RiskManager
from trade_management_unit.lib.common.Utils import *
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
        trade = None
        order = None
        trading_symbol = instrument["trading_symbol"]
        action = instrument["required_action"]
        if action:
            instrument_id = instrument["instrument_token"]
            market_price = instrument["market_data"]["market_price"]
            trade = Trade.fetch_active_trade(instrument_id,trade_session_id,user_id,dummy)
            trade_id = trade.id
            quantity = self.__get_square_off_quantity__(trade_id)
            kite_order_id = self.square_off_order_on_zerodha(trading_symbol,action,quantity,user_id,dummy,market_price)
            frictional_losses = RiskManager().get_frictional_losses(TRADE_TYPE["intraday"],market_price, quantity, action == "BUY")
            order = Order.initiate_order(action.value, instrument_id, trade_id, dummy, kite_order_id, frictional_losses, user_id, quantity,market_price)
            self.__update_and_close_trade__(trade,order.closed_at)
        return (trade,order)

    def square_off_order_on_zerodha(self,trading_symbol,action,quantity,user_id,dummy,market_price):
        kite_order_id = user_id+"__"+str(current_ist())
        if dummy:
            retrived_amount = quantity * market_price
            dummy_record = DummyAccount.objects.get(user_id = user_id)
            current_balance = float(dummy_record.current_balance)
            dummy_record.current_balance = round((current_balance + retrived_amount),2)
            dummy_record.save()
        else:
            order_params = {"trading_symbol":trading_symbol,
                    "exchange": DEFAULT_EXCHANGE,
                    "transaction_type": action,
                    "order_type": "MARKET",
                    "quantity":quantity,
                    "product": "MIS",
                    "validity": "DAY"}
            kite_order_id = Portfolio.initiate_order(order_params)
        return kite_order_id

    def __update_and_close_trade__(self,trade,closed_at):
        if(closed_at):
            net_profit = Trade.get_net_profit(trade.id)
            trade.net_profit = net_profit
            trade.closed_at = closed_at
            trade.is_active = 0
            trade.save()


    def __get_square_off_quantity__(self,trade_id):
        order = Order.fetch_order(trade_id)
        existing_quantity = order.quantity
        return existing_quantity

