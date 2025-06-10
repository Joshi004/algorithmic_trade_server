"""
Constants for Integration Service
"""

# Mapping from TMU frequency format to Zerodha API frequency format
FREQUENCY_MAPPING = {
    "1-minute": "minute",
    "3-minute": "3minute", 
    "5-minute": "5minute",
    "10-minute": "10minute",
    "15-minute": "15minute", 
    "30-minute": "30minute",
    "60-minute": "60minute",
    "1-day": "day"
} 