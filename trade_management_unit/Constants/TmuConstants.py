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

class OrderType(Enum):
    """An enum to represent the order type of the trade."""
    BUY = "buy"
    SELL = "sell"


# Other constants
PI = 3.14
GREETING = "Hello, world!"
FREQUENCY = ["minute","3minute","5minute","10minute","15minute","30minute","60minute","day"]
NUM_CANDLES_FOR_TREND_ANALYSIS = 200
FREQUENCY_STEPS = {
    "10minute" : ["10minute","60minute","day"],
    "5minute" : ["5minute","30minute","day"],
    "15minute" : ["15minute","60minute","day"],
    "day" : ["day","day","day"],
}
