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
    }
    def __init__(self):
        pass

    def get_eligible_instruments(self):
        symbols = ["itc","cdsl","idfc","ongc"]
        eligible_instruments = []
        for symbol in symbols:
            eligible  = is_eligible(symbol)
            if (eligible):
                eligible_instruments.push(symbol)
        return eligible_instruments


    def __fetch_hostorical_data(self, symbol, interval, number_of_candles):
        #Check of 1 minute and 1 day and 15 min
        end_date = datetime.now()

        if "minute" in interval:
            minutes = int(interval.replace("minute", ""))
            start_date = end_date - timedelta(minutes=minutes*number_of_candles)
        elif interval == "day":
            start_date = end_date - timedelta(days=number_of_candles)

        hostorical_data = FetchData().fetch_candle_data(symbol, start_date, end_date, interval)
        return hostorical_data


    def is_eligible(self,symbol,trade_freq):
        frq_steps = UDTSScanner.FREQUENCY_STEPS[trade_freq]
        number_of_candles = UDTSScanner.NUM_CANDLES_FOR_TREND_ANALYSIS

        level_2_data = self.__fetch_hostorical_data(symbol,frq_steps[2],number_of_candles)
        level_1_data = self.__fetch_hostorical_data(symbol,frq_steps[1],number_of_candles)
        level_0_data = self.__fetch_hostorical_data(symbol,frq_steps[0],number_of_candles)

        level_2_chart = CandleChart(level_2_data)
        level_1_chart = CandleChart(level_1_data)
        level_0_chart = CandleChart(level_0_data)
        
        level_2_chart.set_trend_and_deflection_points()
        level_1_chart.set_trend_and_deflection_points()
        level_0_chart.set_trend_and_deflection_points()


        target_trend = level_2_chart.trend
        if(level_1_chart.trend == target_trend and level_0_chart.trend == target_trend):
            level_0_chart.normalise_deflection_points()
            level_0_chart.set_trading_levels_and_ratios()
            if(level_0_chart.reward_risk_ratio > 2 ):
                return True 
        else:
            return False