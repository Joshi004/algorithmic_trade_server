import json
import time
from django.core import serializers
from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.FetchData import FetchData
from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.CandleChart import CandleChart
from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoFactory import TrackerAlgoFactory
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerSingletonMeta import ScannerSingletonMeta
from trade_management_unit.lib.Instruments.Instruments import Instruments
from trade_management_unit.Constants.TmuConstants import *
from channels.db import database_sync_to_async

import pandas as pd
import concurrent.futures
import threading
from datetime import datetime, timedelta
class UDTSScanner(metaclass=ScannerSingletonMeta):

    def __init__(self,trade_freq,tracking_algorithm):
        self.trade_sessions = {} # Stores All the KiteUser instace refs
        self.trade_freqency = trade_freq
        self.tracking_algorithm = tracking_algorithm
     
    def __str__(self):
        idintifier = self.trade_freqency+"__"+self.tracking_algorithm
        return idintifier

    def register_trade_session(self,trade_sesion):
        self.trade_sessions[str(trade_sesion)] = trade_sesion

    def scan_in_seperate_trhread(self,all_instruments):
        counter = 0
        while(True):
            counter += 1
            eligible_instruments = []
            print("------TYoe OF All Instruments",type(all_instruments))
            for instrument in all_instruments:
                symbol = instrument["trading_symbol"]
                token = instrument["instrument_token"]
                is_eligible,eligibility_obj = self.is_eligible(symbol)
                if ( 1 or is_eligible):
                    symbol_data_points = eligibility_obj[self.trade_freqency]["chart"]
                    instrument = {
                        "trading_symbol":symbol,
                        "instrument_token":token,
                        "view" : eligibility_obj["effective_trend"],
                        "support_price" : symbol_data_points.trading_pair["support"] or 1,
                        "resistance_price" : symbol_data_points.trading_pair["resistance"] or 1000,
                        "trade_freqency" : self.trade_freqency
                        }
                    print("Adding to eligible list",instrument)
                    instrument["required_action"] = self.__get_required_actions__(instrument)
                    eligible_instruments.append(instrument)
            # Reformat eligible_instruments first and send array of objects
            self.add_tokens_to_subscribed_tracker_sessiosn(eligible_instruments)
            time.sleep(30)
            print("restrting Scan - ",counter)

    def __get_required_actions__(self,instrument):
        print("Check Volume COnstraints and also min ratio if needed ")
        required_action =None
        if (instrument["view"] == View.LONG):
            required_action = OrderType.BUY.value
        elif(instrument["view"] == View.SHORT):
            required_action = OrderType.SELL.value
        else:
            required_action = None
        return required_action
    
    def add_tokens_to_subscribed_tracker_sessiosn(self,eligible_instruments):
        for identifier in self.trade_sessions:
            trade_session = self.trade_sessions[identifier]
            trade_session.add_tokens(eligible_instruments)  


    def fetch_instruments_from_db(self):
        search_params = {"exchange": "NSE", "segment": "NSE", "instrument_type": "EQ", "page_length": 5000}
        all_instruments = Instruments().fetch_instruments(search_params)["data"]
        downloaded = ["ITC", "ONGC", "PNB", "zomato"]
        
        filtered_instruments = [
            instrument for instrument in all_instruments
            if instrument.get('name', '') != '' and
            instrument.get('trading_symbol', '') in downloaded
        ]
        return filtered_instruments


    def fetch_instrument_tokens_and_start_tracking(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit((self.fetch_instruments_from_db))
            result = future.result()
        self.scan_and_add_instruments_for_tracking(result)


    def scan_and_add_instruments_for_tracking(self,all_instruments):
        scanner_thread = threading.Thread(target=self.scan_in_seperate_trhread,args=(all_instruments,))
        scanner_thread.setDaemon(True)
        scanner_thread.start()

        


    def __fetch_hostorical_data(self, symbol, interval, number_of_candles,trade_date=None):
        #Check of 1 minute and 1 day and 15 min
        # fetch From NSE
        end_date = trade_date if trade_date else datetime.today()
        if "minute" in interval:
            minutes = int(interval.replace("minute", ""))
            start_date = end_date - timedelta(minutes=minutes*number_of_candles)
        elif interval == "day":
            start_date = end_date - timedelta(days=number_of_candles)
        # hostorical_data = FetchData().fetch_from_nse(symbol, start_date, end_date)
        hostorical_data = FetchData().fetch_candle_data(symbol, start_date, end_date)
        return hostorical_data

    def __get_effective_trend(slef,eligibility_obj):
        trends = set()
        for frequency in eligibility_obj:
            chart = eligibility_obj[frequency]["chart"]
            trends.add(chart.trend)
        effective_ternd = trends.pop() if len(trends) == 1 else None
        return effective_ternd
    
    def __get_deflection_points_scope(self,base_chart):
        price_list = base_chart.price_list
        price_list_df = pd.DataFrame(price_list)
        price_list_df["diff"] = price_list_df["high"] - price_list_df["low"]
        average_candle_span = price_list_df["diff"].mean()
        return float(average_candle_span)
    # This is causing deflection point strength to go NAN check this 

    def is_eligible(self,symbol):
        trade_freq =  self.trade_freqency
        frq_steps = FREQUENCY_STEPS[trade_freq]
        number_of_candles = NUM_CANDLES_FOR_TREND_ANALYSIS
        
        eligibility_obj = {}
        for index in range(0,len(frq_steps)):
            freq = frq_steps[index]
            eligibility_obj[freq] = {}
            eligibility_obj[freq]["data"] = self.__fetch_hostorical_data(symbol,frq_steps[index],number_of_candles)
            eligibility_obj[freq]["chart"] = CandleChart(symbol,frq_steps[index],eligibility_obj[freq]["data"])
            eligibility_obj[freq]["chart"].set_trend_and_deflection_points()
    
        deflection_points_scope =  self.__get_deflection_points_scope(eligibility_obj[frq_steps[-1]]["chart"])  
        eligibility_obj[trade_freq]["chart"].normalise_deflection_points(deflection_points_scope)
        eligibility_obj[trade_freq]["chart"].set_trading_levels_and_ratios()
        effective_trend = self.__get_effective_trend(eligibility_obj)
        eligibility_obj["effective_trend"] = effective_trend
        
        reward_risk_ratio = eligibility_obj[trade_freq]["chart"].trading_pair["reward_risk_ratio"] if "reward_risk_ratio" in eligibility_obj[trade_freq]["chart"].trading_pair else 0
        if(effective_trend == "BULLISH"):
            if(reward_risk_ratio > 2 ):
                return True, eligibility_obj
        elif(effective_trend == "BEARISH"):
            if(reward_risk_ratio < 0.5 ):
                return True, eligibility_obj
        return False,eligibility_obj

            
            
    def get_udts_eligibility(self,symbol,trade_freq):
        is_tradable,eligibility_obj =  self.is_eligible(symbol,trade_freq)
        result = eligibility_obj[trade_freq]["chart"]
        response_obj = {
            "data":{
            "price_list" : result.price_list,
            "trend":result.trend,
            "effective_trend" : eligibility_obj["effective_trend"],
            "deflection_points":result.deflection_points,
            "trading_pair":result.trading_pair,
            "average_candle_span":result.average_candle_span,
            "rounding_factor":result.rounding_factor,
            "valid_pairs":result.valid_pairs,
            "market_price":result.market_price,
            "up_scope":result.up_scope,
            "down_scope":result.down_scope,
            },
            "meta":{
            "interval":result.interval,
            "symbol":result.symbol,
            }
        }
        return response_obj