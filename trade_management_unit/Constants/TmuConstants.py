from enum import Enum

class PriceZone(Enum):
    """An enum to represent the price zone of the current price."""
    RESISTANCE_BREAKOUT = "resistance_breakout"
    SUPPORT_BREAKOUT = "support_breakout"
    RANGE = "range"

class View(Enum):
    """An enum to represent the view of the trade."""
    LONG = "long"
    SHORT = "short"

class Trends(Enum):
    """An enum to represent the trend of a stock."""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDETREND = "sidetrend"
    
    @classmethod
    def choices(cls):
        return [(member.value, member.value) for member in cls]

class OrderType(Enum):
    """An enum to represent the order type of the trade."""
    BUY = "buy"
    SELL = "sell"

class TradeType(Enum):
    EQUITY_DELIVERY = "equity_delivery"
    EQUITY_INTRADAY = "equity_intraday"
    EQUITY_FUTURES = "equity_futures"
    EQUITY_OPTIONS = "equity_options"
    CURRENCY_FUTURES = "currency_futures"
    CURRENCY_OPTIONS = "currency_options"
    COMMODITY_FUTURES = "commodity_futures"
    COMMODITY_OPTIONS = "commodity_options"



# Other constants
PI = 3.14
GREETING = "Hello, world!"
TRADE_TYPE = {"intraday":"equity_intraday"}
DEFAULT_EXCHANGE = "NSE"
TRADE_THRESHHOLD_PER_MINUTE = 100000 
FREQUENCY = ["minute","3minute","5minute","10minute","15minute","30minute","60minute","day"]
NUM_CANDLES_FOR_TREND_ANALYSIS = 200
FREQUENCY_STEPS = {
    "10minute" : ["10minute","60minute","day"],
    "5minute" : ["5minute","30minute","day"],
    "15minute" : ["15minute","60minute","day"],
    "day" : ["day","day","day"],
}
