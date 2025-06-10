from enum import Enum

class Trends(Enum):
    """An enum to represent the trend of a stock."""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDETREND = "sidetrend"

class OrderType(Enum):
    """An enum to represent the order type of the trade."""
    BUY = "buy"
    SELL = "sell"

# Scanner algorithm constants
DEFAULT_EXCHANGE = "NSE"
NUM_CANDLES_FOR_TREND_ANALYSIS = 200
MINIMUM_REWARD_RISK_RATIO = 2
MAXIMUM_REWARD_RISK_RATIO = 3
FRICTION_COEFFECIENT = 0.2  # Trading costs consideration

# Frequency configuration
FREQUENCY_STEPS = {
    "1-minute": ["1-minute", "10-minute", "60-minute"],
    "3-minute": ["3-minute", "15-minute", "60-minute"],
    "5-minute": ["5-minute", "30-minute", "60-minute"],
    "10-minute": ["10-minute", "30-minute", "60-minute"],
    "15-minute": ["15-minute", "60-minute", "1-day"],
}
SCOPE_COLLECTION_FREQ_INDEX = 0  # Freq index for scope calculation

# Market timing constants
MARKET_OPEN_TIME = {"hour": 9, "minute": 15}
MARKET_CLOSE_TIME = {"hour": 3, "minute": 30}

# Volume threshold
TRADE_THRESHHOLD_PER_MINUTE = 10000 