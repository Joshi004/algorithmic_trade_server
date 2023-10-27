import json
import time as tm
from django.core import serializers
from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.FetchData import FetchData
from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.CandleChart import CandleChart
from trade_management_unit.lib.Algorithms.TrackerAlgos.TrackerAlgoFactory import TrackerAlgoFactory
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerSingletonMeta import ScannerSingletonMeta
from trade_management_unit.lib.Instruments.Instruments import Instruments
from  trade_management_unit.models.Instrument import Instrument
from trade_management_unit.lib.Trade.trade import Trade
from trade_management_unit.Constants.TmuConstants import *
from trade_management_unit.models.AlgoUdtsScanRecord import AlgoUdtsScanRecord
from trade_management_unit.models.Database import Database
from trade_management_unit.lib.TradeSession.RiskManager import RiskManager
from channels.db import database_sync_to_async

import pandas as pd
import concurrent.futures
import threading
from datetime import datetime, timedelta, time

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
            print("!!!! Fix Coroutine Error  !!!!")
            instrument_counter = 0
            eligible_instrument_counter = 0
            scan_start_time = datetime.now()
            for instrument in all_instruments:
                instrument_counter+=1
                symbol = instrument["trading_symbol"]
                token = instrument["instrument_token"]
                print("\n\n\n")
                print("Scanning Instrument now ",symbol)
                is_eligible,eligibility_obj = self.is_eligible(symbol,token)
                print("Instrument Number",instrument_counter)
                if (is_eligible):
                    instrument_id = Instrument.objects.get(trading_symbol=symbol,exchange=DEFAULT_EXCHANGE).id
                    eligible_instrument_counter += 1
                    print("FOUND NEXT ELIGIBLE -- - ",eligible_instrument_counter,symbol)
                    symbol_data_points = eligibility_obj[self.trade_freqency]["chart"]
                    instrument = {
                        "instrument_id":instrument_id,
                        "trading_symbol":symbol,
                        "instrument_token":token,
                        "trade_freqency" : self.trade_freqency,
                        "effective_trend" : eligibility_obj["effective_trend"],
                        "support_price" : symbol_data_points.trading_pair["support"] or 1,
                        "resistance_price" : symbol_data_points.trading_pair["resistance"] or 1000,
                        "support_strength" : symbol_data_points.trading_pair["support_strength"] or 0,
                        "resistance_strength" : symbol_data_points.trading_pair["resistance_strength"] or 0,
                        "movement_potential" : symbol_data_points.average_candle_span,
                        "market_data" : {
                            "volume" : symbol_data_points.volume,
                            "market_price" : symbol_data_points.market_price,
                            "last_quantity" : symbol_data_points.last_quantity
                        }
                        }
                    instrument["required_action"] = self.__get_required_actions__(instrument)
                    print("Sunscribing To ",instrument["trading_symbol"])
                    # eligible_instruments.append(instrument)
                    self.add_tokens_to_subscribed_tracker_sessiosn([instrument])
                else:
                    print(instrument["trading_symbol"], "is Not Eliggible")
            scan_end_time = datetime.now()
            tm.sleep(30)
            print("restrting Scan - ",counter,"Last Scan Time",(scan_end_time - scan_start_time))

    def mark_into_scan_records(self,trade_id,instrument):  
  
       AlgoUdtsScanRecord.add_entry(
            instrument_id = instrument["instrument_id"],
            market_price=instrument["market_data"]["market_price"],
            support_price=instrument["support_price"],
            resistance_price=instrument["resistance_price"],
            support_strength=instrument["support_strength"],
            resistance_strength=instrument["resistance_strength"],
            effective_trend=instrument["effective_trend"].value,
            trade_candle_interval=instrument["trade_freqency"],
            movement_potential=instrument["movement_potential"],
            trade_id=trade_id
        )

    def __get_required_actions__(self,instrument):
        print("Check Volume COnstraints and also min ratio if needed ")
        required_action =None
        if (instrument["effective_trend"] == Trends.UPTREND):
            required_action = OrderType.BUY.value
        elif(instrument["effective_trend"] == Trends.DOWNTREND):
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
        # downloaded = ["ITC", "ONGC", "PNB", "zomato"]
        
        # filtered_instruments = [
        #     instrument for instrument in all_instruments
        #     if instrument.get('name', '') != '' and
        #     instrument.get('trading_symbol', '') in downloaded
        # ]
        return all_instruments


    def fetch_instrument_tokens_and_start_tracking(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit((self.fetch_instruments_from_db))
            result = future.result()
        self.scan_and_add_instruments_for_tracking(result)


    def scan_and_add_instruments_for_tracking(self,all_instruments):
        scanner_thread = threading.Thread(target=self.scan_in_seperate_trhread,args=(all_instruments,))
        scanner_thread.setDaemon(True)
        scanner_thread.start()

    def get_stored_data(self, symbol, interval):
        database = Database()
    # Define the table name
        table_name = f"hd__{interval}__{symbol}"

        # Check if the table exists
        if not database.table_exists(table_name):
            # If not, create the table
            database.create_hd_table(table_name)

        # Fetch all data from the table
        historical_data = database.fetch_history_data(table_name)
        return list(historical_data)
        

    def __fetch_hostorical_data(self,symbol, token, interval, number_of_candles, trade_date=None):
        # Initialize end_date and historical_data
        end_date = trade_date if trade_date else datetime.now()
        historical_data = []
        stored_data = self.get_stored_data(symbol,interval)
        last_stored_date = None
        if (stored_data and len(stored_data)):
            last_record_date = stored_data[-1]["date"]

        print("History from data",len(stored_data))

        while (len(historical_data) < number_of_candles+1 and end_date.year > 2019):
            # Skip non-trading hours (before 9:15 or after 15:30)
            if end_date.time() < time(9, 15) or end_date.time() > time(15, 30):
                # Move to the previous trading day
                end_date = end_date.replace(hour=15, minute=30) - timedelta(days=1)

            # Skip weekends (Saturday and Sunday)
            while end_date.weekday() >= 5:
                # Move to the previous day
                end_date -= timedelta(days=1)

            # Calculate start_date based on the current length of historical_data
            if last_stored_date:
                start_date = last_record_date
            elif "minute" in interval:
                minutes = int(interval.replace("minute", ""))
                start_date = end_date - timedelta(minutes=minutes*(number_of_candles))
            elif interval == "day":
                start_date = end_date - timedelta(days=number_of_candles)

            # print("----- Getting Historical data symbol: ", token, " Total CAndles : ",len(historical_data),"  Time Diff: ",end_date-start_date," From: ",end_date," To: ",start_date)
            new_data = FetchData().fetch_data_from_zerodha(token, start_date, end_date,interval)

            # Prepend new_data to historical_data
            historical_data = stored_data + new_data + historical_data
            stored_data = []

            # Update end_date for the next iteration
            end_date = start_date

        # If we fetched more data than needed, trim the excess
        if len(historical_data) > number_of_candles:
            historical_data = historical_data[:number_of_candles]
        print("Fetched Historical Data for ",symbol,interval)
        Database().update_historical_data(symbol,interval,historical_data)           
        return historical_data


    def __get_effective_trend(slef,eligibility_obj):
        trends = set()
        for frequency in eligibility_obj:
            chart = eligibility_obj[frequency]["chart"]
            trends.add(chart.trend)
        effective_ternd = trends.pop() if len(trends) == 1 else Trends.SIDETREND
        return effective_ternd
    
    def __get_deflection_points_scope(self,base_chart):
        price_list = base_chart.price_list
        price_list_df = pd.DataFrame(price_list)
        price_list_df["diff"] = price_list_df["high"] - price_list_df["low"]
        average_candle_span = price_list_df["diff"].mean()
        return float(average_candle_span)
    # This is causing deflection point strength to go NAN check this 

    def is_eligible(self,symbol,token):
        trade_freq =  self.trade_freqency
        frq_steps = FREQUENCY_STEPS[trade_freq]
        number_of_candles = NUM_CANDLES_FOR_TREND_ANALYSIS
        quote  = Trade().get_quotes({"symbol" : symbol, "exchange" : DEFAULT_EXCHANGE})
        quote_data = quote["data"][DEFAULT_EXCHANGE+":"+symbol.upper()] 
        is_volume_eligible = self.get_volume_eligibility(quote_data)        
        eligibility_obj = {}
        
        if (not is_volume_eligible):
            print("Volume Not Eligible For",symbol)
            return False , eligibility_obj
        
        for index in range(0,len(frq_steps)):
            freq = frq_steps[index]
            eligibility_obj[freq] = {}
            eligibility_obj[freq]["data"] = self.__fetch_hostorical_data(symbol,token,frq_steps[index],number_of_candles)
            eligibility_obj[freq]["chart"] = CandleChart(symbol,token,quote_data["last_price"],quote_data["volume"],quote_data["last_quantity"],frq_steps[index],eligibility_obj[freq]["data"])
            eligibility_obj[freq]["chart"].set_trend_and_deflection_points()
    
        deflection_points_scope =  self.__get_deflection_points_scope(eligibility_obj[frq_steps[-1]]["chart"])  
        eligibility_obj[trade_freq]["chart"].normalise_deflection_points(deflection_points_scope)
        eligibility_obj[trade_freq]["chart"].set_trading_levels_and_ratios()
        effective_trend = self.__get_effective_trend(eligibility_obj)
        eligibility_obj["effective_trend"] = effective_trend
        
        reward_risk_ratio = eligibility_obj[trade_freq]["chart"].trading_pair["reward_risk_ratio"] if "reward_risk_ratio" in eligibility_obj[trade_freq]["chart"].trading_pair else 0
        if(effective_trend == Trends.UPTREND):
            if(reward_risk_ratio > 2 ):
                return True, eligibility_obj
        elif(effective_trend == Trends.DOWNTREND):
            if(reward_risk_ratio < 0.5 ):
                return True, eligibility_obj
        return False,eligibility_obj

    def get_volume_eligibility(self, quote):
        self.volume = quote["volume"]
        
        # Define market open and close times
        market_open_time = datetime.now().replace(hour=9, minute=15)
        market_close_time = datetime.now().replace(hour=15, minute=30)
        
        # Get current time
        current_time = datetime.now()
        
        # Calculate total minutes from market open to current time or total trade duration
        if current_time < market_open_time:
            # If current time is before market open, consider total trade duration of a day
            total_minutes = int((market_close_time - market_open_time).total_seconds() / 60)
        elif current_time > market_close_time:
            # If current time is after market close, consider end time as market close
            current_time = market_close_time
            total_minutes = int((current_time - market_open_time).total_seconds() / 60)
        else:
            # If current time is within trading hours
            total_minutes = int((current_time - market_open_time).total_seconds() / 60)
        
        # Calculate volume per minute
        volume_per_minute = self.volume / total_minutes
        trade_amount_per_minute = quote["last_price"]*volume_per_minute 
        # Check if volume per minute is greater than threshold
        if trade_amount_per_minute > TRADE_THRESHHOLD_PER_MINUTE:
            return True
        else:
            return False
            
            
    def get_udts_eligibility(self,symbol,trade_freq):
        print("get token and send hereh !!! nOt Working !!!!")
        # is_tradable,eligibility_obj =  self.is_eligible(symbol,trade_freq)
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