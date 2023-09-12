class CandleChart:
    def __init__(self,price_list):
        self.price_list = price_list
        self.trend = None
        self.interval = None
        self.deflection_points = None
        self.average_candle_span = None
        self.rounding_factor = None
        self.symbol = None
        self.reward_risk_ratio = 0
        self.trading_levels = {
            "support" : None,
            "resistance" : None
        }

    def set_trend_and_deflection_points(self):
        price_list= self.price_list
        # This function returns the trend and the deflection points of a price list based on candlestick charting
        def add_deflection_point(direction, price, stoping_potential, distance, frequency, progression_potential,deflection_index,reversal_index):
            deflection_points.append({
                "direction" : direction, # direction: up or down, indicating the direction of the new trend
                "price" : price, # price: the price at which the deflection point occurs
                "stoping_potential" : stoping_potential, # stoping_potential: the difference between the price of the previous deflection point and the price of the current one
                "distance" : distance,# distance: the number of candles between the current deflection point and most recent candle
                "frequency" : frequency, # frequency: not used in this function, but could be used to measure how often deflection points occur
                "progression_potential" : progression_potential, # progression_potential: not used in this function, but could be used to measure how far the price could move in the new direction
                "deflection_index" : deflection_index, # Candle From where deflection is visible
                "reversal_index" : reversal_index # Index of the candle reversing the trend
                
            })


        deflection_points = []
        candle = Candle(price_list[0])
        swing_max = candle.high
        swing_min = candle.low
        swing_max_index = swing_min_index = 0
        # Initialize the trend based on the first candle colour
        is_bullish_trend = (candle.colour == GREEN)
        # Initialize the last bullish and bearish candles
        last_bullish_index = 0 if is_bullish_trend else None
        last_bearish_index = None if is_bullish_trend else 0
        last_bullish_candle = Candle(price_list[0]) if is_bullish_trend else None
        last_bearish_candle = None if is_bullish_trend else Candle(price_list[0])
                # Initialize the first deflection point based on the first candle colour
        add_deflection_point(
            direction = "up" if is_bullish_trend else "down",
            price = swing_min if is_bullish_trend else swing_max,
            stoping_potential = 0,
            distance = len(price_list),
            frequency = None,
            progression_potential = None,
            deflection_index = 0,
            reversal_index = 0
        )
        
        for i, price in enumerate(price_list):
            candle = Candle(price)
            last_deflection_point = deflection_points[-1] 
            # Set swing peaks
            if(candle.high >= swing_max):
                swing_max = candle.high
                swing_max_index = i
            if(candle.low <= swing_min):
                swing_min = candle.low
                swing_min_index = i
            
            if((candle.colour == GREEN) or (candle.colour == WHITE and is_bullish_trend)):
                last_bullish_index = i
                last_bullish_candle = candle
                
                if(not is_bullish_trend): # this is a bullish candle in existing bearish trend 
                    if(candle.close > last_bearish_candle.open): # trend changed to bullish
                        is_bullish_trend = True                
                        last_deflection_point["progression_potential"] = last_deflection_point["price"] - candle.open
                        add_deflection_point(
                            direction = "up",
                            price = swing_min,
                            stoping_potential = last_deflection_point["price"] - swing_min,
                            distance = len(price_list) - swing_min_index,
                            frequency = None,
                            progression_potential = None,
                            deflection_index = swing_min_index,
                            reversal_index = i
                        )
                        swing_max,swing_min, =  candle.high,candle.low
                        swing_max_index = swing_min_index = i
            
            elif((candle.colour == RED) or (candle.colour == WHITE and not is_bullish_trend)):
                last_bearish_index = i
                last_bearish_candle = candle
                
                if(is_bullish_trend): # this is a bearish candle in existing bullish trend 
                    if(candle.close < last_bullish_candle.open): # trend changed to bearish
                        is_bullish_trend = False                
                        last_deflection_point["progression_potential"] = candle.open - last_deflection_point["price"]
                        add_deflection_point(
                            direction = "down",
                            price = swing_max,
                            stoping_potential = swing_max - last_deflection_point["price"],
                            distance = len(price_list) - swing_max_index,
                            frequency = None,
                            progression_potential = None,
                            deflection_index = swing_max_index,
                            reversal_index = i
                        )
                        swing_max,swing_min, =  candle.high,candle.low
                        swing_max_index = swing_min_index = i
        deflection_points[-1]["progression_potential"] = price_list[-1]["Open"] - deflection_points[-1]["price"]
        
        # Format the result string with the trend and the number of deflection points
        result = f"The trend is {'Bullish' if is_bullish_trend else 'Bearish'} and there are {len(deflection_points)} deflection points."
        #last Progression Potential is never set 
        return {"trend" : result,"deflection_points" : deflection_points}
    
    def normalise_deflection_points(self):
        def custom_round(num,factor):
            result  = (num//factor) * factor
            result = round(result,1)
            return result
            
        price_list_df = pd.DataFrame(price_list)
        def_list_df = pd.DataFrame(def_list)
    #     print(def_list_df["price"])
        price_list_df["diff"] = price_list_df["High"] - price_list_df["Low"]
        average_candle_span = price_list_df["diff"].mean()
        
        if (not scope):
            market_price = price_list[-1]["Close"]
            up_scope = market_price + 2*average_candle_span
            down_scope = market_price - 2*average_candle_span
            scope = [up_scope,down_scope]     
        rounding_factor = round((average_candle_span / 10),1)
        def_list_df["price"] = custom_round(def_list_df["price"],rounding_factor)
        counts = def_list_df["price"].value_counts()
        def_list_df["frequency"] = def_list_df["price"].map(counts)
        deflection_strength = (def_list_df["stoping_potential"]*def_list_df["progression_potential"])/def_list_df["distance"] * ((def_list_df["stoping_potential"]+def_list_df["progression_potential"])**(def_list_df["frequency"]))
        deflection_strength = round(deflection_strength,2) 
        condition = (def_list_df["price"].astype(int) < int(scope[0])) & (def_list_df["price"].astype(int) > int(scope[1]))
        def_list_df["strength"] = deflection_strength.where(condition, 0)
        # Get the maximum value of strength
        max_strength = def_list_df["strength"].max()
        # Normalize strength to percentages
        def_list_df["strength"] = abs(def_list_df["strength"] / max_strength * 5)

        return price_list_df,def_list_df,scope 
    

    def set_trading_levels_and_ratios(self):
        pass