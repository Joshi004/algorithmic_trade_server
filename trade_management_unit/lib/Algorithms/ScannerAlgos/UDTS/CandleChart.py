from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.Candle import Candle
import pandas as pd
from trade_management_unit.Constants.TmuConstants import *
class CandleChart:
    def __init__(self,token,symbol,market_price,trade_volume,last_quantity,trade_freq,price_list):
        self.price_list = price_list
        self.market_price = market_price
        self.last_quantity = last_quantity
        self.volume = trade_volume
        self.instrument_token = token
        self.interval = trade_freq
        self.deflection_points = []
        self.trading_pair= {}
        self.trend = None
        self.average_candle_span = None
        self.rounding_factor = None
        self.symbol = symbol
        self.valid_pairs=None
    

    def __add_deflection_point(self,direction, price, stoping_potential, distance, frequency, progression_potential,deflection_index,reversal_index):
        self.deflection_points.append({
            "direction" : direction, # direction: up or down, indicating the direction of the new trend
            "price" : price, # price: the price at which the deflection point occurs
            "stoping_potential" : stoping_potential, # stoping_potential: the difference between the price of the previous deflection point and the price of the current one
            "distance" : distance,# distance: the number of candles between the current deflection point and most recent candle
            "frequency" : frequency, # frequency: not used in this function, but could be used to measure how often deflection points occur
            "progression_potential" : progression_potential, # progression_potential: not used in this function, but could be used to measure how far the price could move in the new direction
            "deflection_index" : deflection_index, # Candle From where deflection is visible
            "reversal_index" : reversal_index # Index of the candle reversing the trend
            
        })

    def set_trend_and_deflection_points(self):
        # This function returns the trend and the deflection points of a price list based on candlestick charting
        candle = Candle(self.price_list[0])
        swing_max = candle.high
        swing_min = candle.low
        swing_max_index = swing_min_index = 0
        # Initialize the trend based on the first candle colour
        is_bullish_trend = (candle.colour == "GREEN")
        # Initialize the last bullish and bearish candles
        last_bullish_candle = Candle(self.price_list[0]) if is_bullish_trend else None
        last_bearish_candle = None if is_bullish_trend else Candle(self.price_list[0])
                # Initialize the first deflection point based on the first candle colour
        
        self.__add_deflection_point(
            direction = "up" if is_bullish_trend else "down",
            price = swing_min if is_bullish_trend else swing_max,
            stoping_potential = 0,
            distance = len(self.price_list),
            frequency = None,
            progression_potential = None,
            deflection_index = 0,
            reversal_index = 0
        )
        
        for i, price in enumerate(self.price_list):
            candle = Candle(price)
            last_deflection_point = self.deflection_points[-1] 
            # Set swing peaks
            if(candle.high >= swing_max):
                swing_max = candle.high
                swing_max_index = i
            if(candle.low <= swing_min):
                swing_min = candle.low
                swing_min_index = i
            
            if((candle.colour == "GREEN") or (candle.colour == "WHITE" and is_bullish_trend)):
                last_bullish_candle = candle
                
                if(not is_bullish_trend): # this is a bullish candle in existing bearish trend 
                    if(candle.close > last_bearish_candle.open): # trend changed to bullish
                        is_bullish_trend = True                
                        last_deflection_point["progression_potential"] = last_deflection_point["price"] - candle.open
                        self.__add_deflection_point(
                            direction = "up",
                            price = swing_min,
                            stoping_potential = last_deflection_point["price"] - swing_min,
                            distance = len(self.price_list) - swing_min_index,
                            frequency = None,
                            progression_potential = None,
                            deflection_index = swing_min_index,
                            reversal_index = i
                        )
                        swing_max,swing_min, =  candle.high,candle.low
                        swing_max_index = swing_min_index = i
            
            elif((candle.colour == "RED") or (candle.colour == "WHITE" and not is_bullish_trend)):
                last_bearish_candle = candle
                
                if(is_bullish_trend): # this is a bearish candle in existing bullish trend 
                    if(candle.close < last_bullish_candle.open): # trend changed to bearish
                        is_bullish_trend = False             
                        last_deflection_point["progression_potential"] = candle.open - last_deflection_point["price"]
                        self.__add_deflection_point(
                            direction = "down",
                            price = swing_max,
                            stoping_potential = swing_max - last_deflection_point["price"],
                            distance = len(self.price_list) - swing_max_index,
                            frequency = None,
                            progression_potential = None,
                            deflection_index = swing_max_index,
                            reversal_index = i
                        )
                        swing_max,swing_min, =  candle.high,candle.low
                        swing_max_index = swing_min_index = i           
        #Set last progression Potential and trend
        self.deflection_points[-1]["progression_potential"] = self.market_price - self.deflection_points[-1]["price"]        
        # Use Constants File for this 
        self.trend = Trends.UPTREND if is_bullish_trend else Trends.DOWNTREND

    
    def normalise_deflection_points(self,scope_range):
        def custom_round(num,factor):
            result = (num//factor) * factor
            result = round(result,1)
            return result
            
        price_list_df = pd.DataFrame(self.price_list)
        def_list_df = pd.DataFrame(self.deflection_points)
        price_list_df["diff"] = price_list_df["high"] - price_list_df["low"]
        self.average_candle_span = price_list_df["diff"].mean()
        market_price = self.market_price
        self.up_scope = market_price + scope_range
        self.down_scope = market_price - scope_range
        scope = [self.up_scope,self.down_scope]   
            # !!!! Make this configurable   
        self.rounding_factor = round((self.average_candle_span / 10),1)
        self.rounding_factor = 0.5 if self.rounding_factor< 0.5 else self.rounding_factor
        def_list_df["price"] = custom_round(def_list_df["price"],self.rounding_factor)
        counts = def_list_df["price"].value_counts()
        def_list_df["frequency"] = def_list_df["price"].map(counts)
        deflection_strength = (def_list_df["stoping_potential"]*def_list_df["progression_potential"])/def_list_df["distance"] * ((def_list_df["stoping_potential"]+def_list_df["progression_potential"])**(def_list_df["frequency"]))
        deflection_strength = round(deflection_strength,2) 
        condition = (def_list_df["price"].astype(float) < float(scope[0])) & (def_list_df["price"].astype(float) > float(scope[1]))
        def_list_df["strength"] = deflection_strength.where(condition, 0)
        
        # Get the maximum value of strength
        max_strength = def_list_df["strength"].max()
        # Normalize strength to percentages
        def_list_df["strength"] = abs(def_list_df["strength"] / max_strength * 5) if max_strength else 0
        self.deflection_points = def_list_df.to_dict("records")
        return price_list_df,def_list_df,scope 
    

    def set_trading_levels_and_ratios(self,min_reward = 2):
        trading_pair = {"support":None,
                        "resistance":None,
                        "reward_risk_ratio":0,
                        "support":None,
                        "resistance":None,
                        "resistance_strength":None,
                        "support_strength":None,
                        "strength":0}
        
        def_list = self.deflection_points
        price = self.market_price
        valid_pairs = []
        support_points = []
        resist_points=[]
        for point in def_list:
            if (point["price"]<price):
                support_points.append(point)
            elif(point["price"]>price):
                resist_points.append(point)
        if(not len(support_points) or not len(resist_points)):
            self.trading_pair=trading_pair
            return

        print("!! See from where mion rewrad is coming")
        for support in support_points:
            for resist in resist_points:
                if(self.__is_valid_pair(price,support,resist,self.trend,min_reward)):
                    reward_risk_ratio = self.get_reward_risk_ratio(price,support,resist,self.trend)
                    eq_strength = resist["strength"] + support["strength"]
                    valid_pairs.append({"support": support["price"],
                                        "resistance": resist["price"],
                                        "resistance_strength": resist["strength"],
                                        "support_strength": support["strength"],
                                        "strength": eq_strength,
                                        "reward_risk_ratio": reward_risk_ratio})
                
        
        for pair in valid_pairs:
            if(pair["strength"] > trading_pair["strength"]):
                trading_pair = pair
        
        self.valid_pairs = valid_pairs
        self.trading_pair = trading_pair
        return valid_pairs, trading_pair

    def __is_valid_pair(self,price,support,resist,trend,min_reward):
        bottom = price - support["price"]
        top = resist["price"] - price
        product_of_strengts = resist["strength"] * support["strength"]
        print("!!! HAndle harcoding of strength factir here ")
        if (product_of_strengts == 0):
            return False
        if (trend == Trends.UPTREND and MINIMUM_REWARD_RISK_RATIO < top/bottom < MAXIMUM_REWARD_RISK_RATIO ):
            return True
        if (trend == Trends.DOWNTREND  and MINIMUM_REWARD_RISK_RATIO < bottom/top < MAXIMUM_REWARD_RISK_RATIO):
            return True
        return False

    def get_reward_risk_ratio(self,price,support,resist,trend):
        bottom = price - support["price"]
        top = resist["price"] - price
        if (trend == Trends.UPTREND):
            return (top/bottom)
        if(trend == Trends.DOWNTREND):
            return bottom/top
        return 0


