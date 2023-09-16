import json
from django.core import serializers
from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.FetchData import FetchData
from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.CandleChart import CandleChart

from datetime import datetime, timedelta
class UDTSScanner:
    FREQUENCY = ["minute","3minute","5minute","10minute","15minute","30minute","60minute","day"]
    NUM_CANDLES_FOR_TREND_ANALYSIS = 200
    FREQUENCY_STEPS = {
        "10minute" : ["10minute","60minute","day"],
        "5minute" : ["5minute","30minute","day"],
        "15minute" : ["15minute","60minute","day"],
        "day" : ["day","day","day"],
    }
    def __init__(self):
        pass

    def get_eligible_instruments(self):
        symbols = ["itc","cdsl","idfc","ongc"]
        eligible_instruments = []
        for symbol in symbols:
            eligible  = self.is_eligible(symbol)
            if (eligible):
                eligible_instruments.push(symbol)
        return eligible_instruments


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

    def is_eligible(self,symbol,trade_freq):
        frq_steps = UDTSScanner.FREQUENCY_STEPS[trade_freq]
        number_of_candles = UDTSScanner.NUM_CANDLES_FOR_TREND_ANALYSIS
        
        eligibility_obj = {}
        for index in range(0,len(frq_steps)):
            freq = frq_steps[index]
            eligibility_obj[freq] = {}
            eligibility_obj[freq]["data"] = self.__fetch_hostorical_data(symbol,frq_steps[index],number_of_candles)
            eligibility_obj[freq]["chart"] = CandleChart(symbol,frq_steps[index],eligibility_obj[freq]["data"])
            eligibility_obj[freq]["chart"].set_trend_and_deflection_points()
            
        eligibility_obj[trade_freq]["chart"].normalise_deflection_points()
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