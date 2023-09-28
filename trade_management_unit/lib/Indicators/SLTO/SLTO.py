from trade_management_unit.lib.Indicators.IndicitorSingletonMeta import IndicitorSingletonMeta
from trade_management_unit.Constants.TmuConstants import *
from datetime import datetime

class SLTO(): 

    def __init__(self,trade_session_identifier:str,trading_symbol:str,other_params:dict):
        self.symbol = trading_symbol
        self.trading_frequency = other_params["trading_frequency"]
        self.view = other_params["view"]
        self.support_price = other_params["support_price"]
        self.resistance_price = other_params["resistance_price"]
        self.zone_in_time = datetime.now()
        self.price_zone = PriceZone.RANGE
        self.tracking_start_time = datetime.now()
        self.timeout_period = self.get_timeout_period(self.trading_frequency)
        self.required_action = None
        self.prev_price_zone = None
        self.tracking_end_time =None
        self.price_zone_changed = False

    def __str__(self) -> str:
        identifier = self.trading_frequency + "__" +  self.symbol
        return identifier
    
    def get_timeout_period(self, trade_freq):
        division_factor =  20
        # Check if the input is just a unit (day/minute)
        if trade_freq in ['day', 'minute']:
            number = 1
            unit = trade_freq
        else:
            # Extract the number and the unit (minute/day) from trade_freq
            number, unit = int(trade_freq[:-6]), trade_freq[-6:]

        # Convert the number to seconds
        if unit == 'minute':
            number *= 60
        elif unit == 'day':
            number *= 24 * 60 * 60

        # Calculate and return the timeout period
        timeout_period = number // division_factor
        return timeout_period

    def update(self, ltp:float )-> None:
        current_price_zone = self.__get_price_zone(ltp)
        current_time = datetime.now()
        self.price_zone_changed = (self.price_zone != current_price_zone)
        time_delta = int((current_time - self.zone_in_time).total_seconds())
        if(self.price_zone_changed):
            self.zone_in_time = current_time
        self.__set_place_order_action__(current_price_zone,time_delta)
        self.prev_price_zone = self.price_zone
        self.price_zone = current_price_zone

    def __get_price_zone(self,ltp:float):
        if(ltp >= self.resistance_price):
            return PriceZone.RESISTANCE_BREAKOUT
        elif(ltp <= self.support_price):
            return PriceZone.SUPPORT_BREAKOUT
        else:
            return PriceZone.RANGE

    
    def append_information(self,initial_data:dict):
        initial_data["slto"] = {}
        initial_data["slto"]["support_price"] = self.support_price
        initial_data["slto"]["resistance_price"] = self.resistance_price
        initial_data["slto"]["tracking_start_time"] = self.tracking_start_time
        initial_data["slto"]["zone_in_time"] = self.zone_in_time
        initial_data["slto"]["timeout_period"] = self.timeout_period
        initial_data["slto"]["view"] = str(self.view)
        initial_data["slto"]["price_zone"] = (self.price_zone).value
        initial_data["slto"]["prev_price_zone"] = (self.prev_price_zone).value
        initial_data["slto"]["price_zone_changed"] = self.price_zone_changed
        initial_data["slto"]["required_action"] = self.required_action
        initial_data["slto"]["tracking_end_time"] = self.tracking_end_time
        initial_data["slto"]["mark_time"] = datetime.now()

    def __set_place_order_action__(self,current_price_zone:PriceZone,time_delta:int)-> None:
        self.required_action = None
        if(current_price_zone == PriceZone.RESISTANCE_BREAKOUT):
            if(self.view == View.LONG):
                self.required_action = OrderType.SELL
                self.tracking_end_time = datetime.now()
            elif(self.view == View.SHORT and time_delta > self.timeout_period):
                self.required_action = OrderType.BUY
                self.tracking_end_time = datetime.now()
        elif(current_price_zone == PriceZone.SUPPORT_BREAKOUT):
            if(self.view == View.SHORT):
                self.required_action = OrderType.BUY
                self.tracking_end_time = datetime.now()
            elif(self.view == View.LONG and time_delta > self.timeout_period):
                self.required_action = OrderType.SELL
                self.tracking_end_time = datetime.now()
        else:
            pass # Price in Range










