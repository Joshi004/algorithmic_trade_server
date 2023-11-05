from trade_management_unit.lib.Indicators.IndicitorSingletonMeta import IndicitorSingletonMeta
from trade_management_unit.Constants.TmuConstants import *
from trade_management_unit.models.AlgoSltoTrackRecord import AlgoSltoTrackRecord
from datetime import datetime
from trade_management_unit.models.Trade import Trade

from trade_management_unit.models.AlgoUdtsScanRecord import AlgoUdtsScanRecord
class SLTO():

    def __init__(self,trade_id,trading_symbol,instrunent_id,trading_frequency):
        self.symbol = trading_symbol
        self.trading_frequency = trading_frequency
        udts_record = AlgoUdtsScanRecord.fetch_udts_record(trade_id,instrunent_id)
        effective_trend = udts_record.effective_trend
        self.view = View.LONG if effective_trend == Trends.UPTREND else View.SHORT if effective_trend == Trends.DOWNTREND else None
        self.support_price = udts_record.support_price
        self.resistance_price = udts_record.resistance_price
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
        self.price_zone_changed =  False
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

    def mark_into_indicator_records(self,tick,trade_session_id,user_id,dummy):
        instrument_id = tick["instrument_token"]
        trade = Trade.fetch_active_trade(instrument_id,trade_session_id,user_id,dummy)
        trade_id = trade.id
        AlgoSltoTrackRecord.add_indicator_entry(
            market_price=tick["last_price"],
            trade_id = trade_id,
            instrument_id = instrument_id,
            existing_price_zone=tick["indicator_data"]["slto"]["prev_price_zone"],
            next_price_zone=tick["indicator_data"]["slto"]["price_zone"],
            zone_change_time=tick["indicator_data"]["slto"]["mark_time"],
        )

    def append_information(self,initial_data:dict):
        initial_data["indicator_data"] = initial_data["indicator_data"]  if( "indicator_data" in  initial_data)  else {}
        initial_data["indicator_data"]["slto"] = {}
        initial_data["indicator_data"]["slto"]["support_price"] = self.support_price
        initial_data["indicator_data"]["slto"]["resistance_price"] = self.resistance_price
        initial_data["indicator_data"]["slto"]["tracking_start_time"] = self.tracking_start_time
        initial_data["indicator_data"]["slto"]["zone_in_time"] = self.zone_in_time
        initial_data["indicator_data"]["slto"]["timeout_period"] = self.timeout_period
        initial_data["indicator_data"]["slto"]["view"] = str(self.view)
        initial_data["indicator_data"]["slto"]["price_zone"] = (self.price_zone).value
        initial_data["indicator_data"]["slto"]["prev_price_zone"] = (self.prev_price_zone).value
        initial_data["indicator_data"]["slto"]["price_zone_changed"] = self.price_zone_changed
        initial_data["indicator_data"]["slto"]["required_action"] = self.required_action
        initial_data["indicator_data"]["slto"]["tracking_end_time"] = self.tracking_end_time
        initial_data["indicator_data"]["slto"]["mark_time"] = datetime.now()

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
             # Get the current time
            current_time = datetime.now().time()
            # Define the cut-off time as 15:20 and end time as 15:30
            cut_off_time = datetime.strptime(MARKET_CUTOFF_TIME, '%H:%M').time()
            end_time = datetime.strptime(MARKET_END_TIME, '%H:%M').time()
            # Check if the current time is greater than the cut-off time and less than the end time
            if cut_off_time < current_time < end_time:
                if self.view == View.SHORT:
                    self.required_action = OrderType.BUY
                    self.tracking_end_time = datetime.now()
                elif self.view == View.LONG:
                    self.required_action = OrderType.SELL
                    self.tracking_end_time = datetime.now()












