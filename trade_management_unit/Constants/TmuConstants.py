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

class COMMUNICATION_ACTION(Enum):
    INITIATE_TRADE = "initiate_trade"
    TERMINATE_TRADE = "terminate_trade"
    BUY_INSTRUMENT = "buy_instrument"
    SELL_INSTRUMENT = "sell_instrument"
    SUBSCRIBE_INSTRUMENT = "subscribe_instrument"
    UNSUBSCRIBE_INSTRUMENT = "unsubscribe_instrument"
    RANGE_CROSSOVER = "range_crossover"
    BALANCE_ALERT = "balance_alert"
    PRICE_UPDATE = "price_update"
    candle_update = "candle_update"



# Other constants
INDIAN_TIMEZONE = 'Asia/Kolkata'
MARKET_OPEN_TIME = {"hour": 9, "minute":15}
MARKET_CLOSE_TIME = {"hour": 3, "minute":30}
MARKET_CUTOFF_TIME = '14:50'
MARKET_END_TIME = '15:15'
MARGIN_FACTOR=1.5
TRADE_TYPE = {"intraday":"equity_intraday"}
DEFAULT_EXCHANGE = "NSE"
MINIMUM_REQUIRED_BALANCE = 100
TRADE_THRESHHOLD_PER_MINUTE = 10000
FREQUENCY = ["minute", "3minute", "5minute", "10minute", "15minute", "30minute", "60minute", "day"]
NUM_CANDLES_FOR_TREND_ANALYSIS = 200
MINIMUM_REWARD_RISK_RATIO = 2
MAXIMUM_REWARD_RISK_RATIO = 3
FRICTION_COEFFECIENT = 0.2 # Currently Zerodha take alsmost 0.8% of total buy value or sell value so proit amount should be atleast FRICTION_COEFFECIENT/100* price
FREQUENCY_STEPS = {
    "minute": ["minute", "10minute", "60minute"],
    "3minute": ["3minute", "15minute", "60minute"],
    "5minute": ["5minute", "30minute", "60minute"],
    "10minute": ["10minute", "30minute", "60minute"],
    "15minute": ["15minute", "60minute", "day"],
}
SCOPE_COLLECTION_FREQ_INDEX = 0  # This is the freq index from where the scope is calculated for price traversal

