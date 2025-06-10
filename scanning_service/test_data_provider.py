#!/usr/bin/env python
"""
Test script for the Integration Service data provider.
Run this to verify the integration service API calls are working.
"""
import os
import sys
import django

# Setup Django
sys.path.append('/app')  # Adjust based on your Docker setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')
django.setup()

from scanning_service.lib.data_providers import IntegrationServiceProvider
from scanning_service.lib.utils.logger import log


def test_integration_provider():
    """Test the integration service provider functionality"""
    
    # Initialize data provider with a test user ID
    # You'll need to provide a valid user_id for testing
    user_id = "test_user_id"  # Replace with actual user ID
    
    log("=" * 50)
    log("Testing Integration Service Provider")
    log("=" * 50)
    
    provider = IntegrationServiceProvider(user_id)
    
    # Test 1: Get quotes
    log("\n=== Test 1: Get Quotes ===")
    symbol = "RELIANCE"
    exchange = "NSE"
    
    quotes = provider.get_quotes(symbol, exchange)
    if quotes.get("data"):
        log(f"✅ Successfully fetched quotes for {symbol}")
        quote_key = f"{exchange}:{symbol}"
        if quote_key in quotes['data']:
            quote_data = quotes['data'][quote_key]
            log(f"  - Last Price: {quote_data.get('last_price')}")
            log(f"  - Volume: {quote_data.get('volume')}")
            log(f"  - Token: {quote_data.get('instrument_token')}")
    else:
        log(f"❌ Failed to fetch quotes: {quotes.get('meta', {}).get('error')}")
    
    # Test 2: Get historical data
    log("\n=== Test 2: Get Historical Data ===")
    token = "738561"  # Example token for RELIANCE
    interval = "5-minute"
    num_candles = 10
    
    historical_data = provider.fetch_historical_candle_data_from_kite(
        symbol, token, interval, num_candles
    )
    
    if historical_data:
        log(f"✅ Successfully fetched {len(historical_data)} candles")
        if historical_data:
            first_candle = historical_data[0]
            log(f"  - First candle timestamp: {first_candle[0] if isinstance(first_candle, list) else first_candle.get('timestamp')}")
            log(f"  - Candle format: {type(first_candle)}")
    else:
        log("❌ Failed to fetch historical data")
    
    log("\n" + "=" * 50)
    log("Integration Service Provider test completed!")
    log("Note: For instrument data, use TMUServiceProvider instead")
    log("=" * 50)


if __name__ == "__main__":
    try:
        test_integration_provider()
    except Exception as e:
        log(f"Test failed with error: {str(e)}", level="error")
        import traceback
        traceback.print_exc() 