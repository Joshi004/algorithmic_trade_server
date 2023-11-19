import time as tm
from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.CandleChart import CandleChart
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerSingletonMeta import ScannerSingletonMeta
from trade_management_unit.lib.Instruments.Instruments import Instruments
from  trade_management_unit.models.Instrument import Instrument
from trade_management_unit.lib.Trade.trade import Trade as TradeLib
from trade_management_unit.models.Order import Order
from trade_management_unit.models.Trade import Trade
from trade_management_unit.models.DummyAccount import DummyAccount
from trade_management_unit.Constants.TmuConstants import *
from trade_management_unit.lib.Instruments.historical_data.FetchData import FetchData
from trade_management_unit.models.AlgoUdtsScanRecord import AlgoUdtsScanRecord
from trade_management_unit.lib.TradeSession.RiskManager import RiskManager
from trade_management_unit.lib.Portfolio.Portfolio import Portfolio
import pandas as pd
import concurrent.futures
import threading
from datetime import datetime


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

    def scan_in_seperate_trhread(self,all_instruments,user_id,dummy):
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
                current_balance = Portfolio().get_current_balance_including_margin(user_id,dummy)
                if(current_balance < MINIMUM_REQUIRED_BALANCE):
                    print("Not Enough Balance to place Trades ",current_balance)
                    tm.sleep(120)
                    continue
                print("Scanning Instrument now ",symbol)
                is_eligible,eligibility_obj = self.is_eligible(symbol)
                print("Instrument Number",instrument_counter)

                if (is_eligible):
                    instrument_id = token
                    eligible_instrument_counter += 1
                    print("FOUND NEXT ELIGIBLE -- - ",eligible_instrument_counter,symbol)
                    symbol_data_points = eligibility_obj[self.trade_freqency]["chart"]
                    instrument = {
                        "instrument_id":instrument_id,
                        "trading_symbol":symbol,
                        "instrument_token":token,
                        "trade_freqency" : self.trade_freqency,
                        "effective_trend" : eligibility_obj["effective_trend"],
                        "support_price" : symbol_data_points.trading_pair["support"],
                        "resistance_price" : symbol_data_points.trading_pair["resistance"],
                        "support_strength" : symbol_data_points.trading_pair["support_strength"],
                        "resistance_strength" : symbol_data_points.trading_pair["resistance_strength"],
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
                    self.add_tokens_to_subscribed_trade_sessions([instrument])
                else:
                    print(eligibility_obj["message"])
                    print(f"Active Threads {threading.active_count()}")
            scan_end_time = datetime.now()
            tm.sleep(30)
            print("restrting Scan - ",counter,"Last Scan Time",(scan_end_time - scan_start_time))

    def mark_into_scan_records(self,trade_id,tracking_algo_name,instrument):

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
            trade_id=trade_id,
            tracking_algo_name=tracking_algo_name,
            volume=instrument["market_data"]["volume"]
        )
    def process_scanner_actions(self,instrument,user_id,dummy,trade_session_id):
        order = None
        trade = None
        trading_symbol = instrument["trading_symbol"]
        action = instrument["required_action"]
        if action:
            instrument_id = instrument["instrument_id"]
            market_price = instrument["market_data"]["market_price"]
            risk_manager = RiskManager()
            quantity,frictional_losses = risk_manager.get_quantity_and_frictional_losses(action,market_price,instrument["support_price"],instrument["resistance_price"],user_id,dummy,trade_session_id)
            if(quantity>0):
                print("!!! Order from Zerodha",trading_symbol,action)
                margin = self.get_trade_margin(action,market_price,instrument["support_price"],instrument["resistance_price"],quantity)
                trade = Trade.fetch_or_initiate_trade(instrument_id, action,trade_session_id,user_id,dummy,margin)
                trade_id = trade.id
                if(not self.has_active_position(trade_id)):
                    kite_order_id = self.place_order_on_kite(trading_symbol,quantity,action,instrument["support_price"],instrument["resistance_price"],instrument["market_data"]["market_price"],user_id,dummy)
                    order = Order.initiate_order(action, instrument_id, trade_id, dummy, kite_order_id, frictional_losses, user_id, quantity,market_price)
        return (trade,order)

    def has_active_position(self,trade_id):
        orders = Order.objects.filter(trade_id=trade_id)
        if(len(orders)==1):
            return True
        return False

    def get_trade_margin(self,action,market_price,support_price,resistance_price,quantity):
        if(action == OrderType.SELL.value):
            risk = (resistance_price - market_price) * quantity
            margin = MARGIN_FACTOR*risk
            return margin
        else:
            return 0


    def place_order_on_kite(self,trading_symbol,qunatity,action,support_price,resistance_price,market_price,user_id,dummy):
        stoploss = market_price - 0.99*support_price if action == OrderType.BUY else  1.01*support_price - market_price
        squareoff = 1.01*resistance_price - market_price if action == OrderType.BUY else market_price - 0.99*support_price
        if (dummy):
            dummy_account = DummyAccount.objects.get(user_id=user_id)
            current_balance = (dummy_account.current_balance)
            order_amount = qunatity * market_price
            new_balance = float(current_balance) - order_amount
            dummy_account.current_balance = round(new_balance,2)
            dummy_account.save()
            return user_id+"__"+str(datetime.now)
        else:
            print("!!! Check Stoploss and squareoff values properly before this ")
            params = {"trading_symbol":trading_symbol,
                      "qunatity":qunatity,
                      "order_type":action,
                      "product":"BO",
                      "squareoff":squareoff,
                      "stoploss":stoploss,
                      "validity":"IOC",
                      "price":market_price
                      }
            resposne  = Portfolio().place_order(params)
            return resposne.trade_id



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
    
    def add_tokens_to_subscribed_trade_sessions(self,eligible_instruments):
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


    def fetch_instrument_tokens_and_start_tracking(self,user_id,dummy):
        result = self.fetch_instruments_from_db()
        self.scan_and_add_instruments_for_tracking(result,user_id,dummy)


    def scan_and_add_instruments_for_tracking(self,all_instruments,user_id,dummy):
        scanner_thread = threading.Thread(target=self.scan_in_seperate_trhread,args=(all_instruments,user_id,dummy))
        scanner_thread.setDaemon(True)
        scanner_thread.start()


    def __get_effective_trend(self,eligibility_obj):
        trends = set()
        for frequency in eligibility_obj:
            if frequency == "message":
                continue
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

    def is_eligible(self,symbol):
        eligibility_obj = {"message": str(symbol) + " : Eligible"}
        quote  = TradeLib().get_quotes({"symbol" : symbol, "exchange" : DEFAULT_EXCHANGE})
        key = DEFAULT_EXCHANGE+":"+symbol.upper()
        if key not in quote["data"]:
            eligibility_obj["message"] = symbol + " : No Da ta Fetched from quotes"
            return False, eligibility_obj
        token = quote["data"][key]["instrument_token"]
        quote_data = quote["data"][key]
        trade_freq =  self.trade_freqency
        frq_steps = FREQUENCY_STEPS[trade_freq]
        number_of_candles = NUM_CANDLES_FOR_TREND_ANALYSIS
        is_volume_eligible = self.get_volume_eligibility(quote_data)
        if (not is_volume_eligible):
            print("Volume Not Eligible For",symbol)
            eligibility_obj["message"] = symbol + " : Volume not eligible"
            return False, eligibility_obj
        
        for index in range(0,len(frq_steps)):
            freq = frq_steps[index]
            eligibility_obj[freq] = {}
            eligibility_obj[freq]["data"] = FetchData().fetch_historical_candle_data_from_kite(symbol,token,frq_steps[index],number_of_candles)
            if(len(eligibility_obj[freq]["data"]) < NUM_CANDLES_FOR_TREND_ANALYSIS): #For This frequency no data was fetched
                eligibility_obj["message"] = symbol + " : Not Enough Candles For " + str(freq)
                return False , eligibility_obj
            eligibility_obj[freq]["chart"] = CandleChart(symbol,token,quote_data["last_price"],quote_data["volume"],quote_data["last_quantity"],frq_steps[index],eligibility_obj[freq]["data"])
            eligibility_obj[freq]["chart"].set_trend_and_deflection_points()
        # USe Center element for scope
        deflection_points_scope =  self.__get_deflection_points_scope(eligibility_obj[frq_steps[SCOPE_COLLECTION_FREQ_INDEX]]["chart"])
        eligibility_obj[trade_freq]["chart"].normalise_deflection_points(deflection_points_scope)
        eligibility_obj[trade_freq]["chart"].set_trading_levels_and_ratios()
        effective_trend = self.__get_effective_trend(eligibility_obj)
        eligibility_obj["effective_trend"] = effective_trend

        if(not eligibility_obj[trade_freq]["chart"].valid_pairs or len(eligibility_obj[trade_freq]["chart"].valid_pairs)<1):
            eligibility_obj["message"] = symbol + " : No Valid Trading pairs Present"
            return False, eligibility_obj

        reward_risk_ratio = eligibility_obj[trade_freq]["chart"].trading_pair["reward_risk_ratio"] if "reward_risk_ratio" in eligibility_obj[trade_freq]["chart"].trading_pair else 0
        eligibility_obj["message"] = f"{symbol} : {effective_trend.value} , Reward:Risk - {reward_risk_ratio}"
        if(reward_risk_ratio > MINIMUM_REWARD_RISK_RATIO ):
            return True,eligibility_obj

        return False,eligibility_obj

    def get_volume_eligibility(self, quote):
        self.volume = quote["volume"]
        
        # Define market open and close times
        market_open_time = datetime.now().replace(**MARKET_OPEN_TIME)
        market_close_time = datetime.now().replace(**MARKET_CLOSE_TIME)
        
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
        is_tradable,eligibility_obj =  self.is_eligible(symbol)
        result = eligibility_obj[trade_freq]["chart"]
        response_obj = {
            "data":{
            "price_list" : result.price_list,
            "trend":result.trend.value,
            "effective_trend" : eligibility_obj["effective_trend"].value,
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
