#!/usr/bin/env python
"""
Test script for the TMU service provider.
Run this to verify the TMU service API calls are working.
"""
import os
import sys
import django

# Setup Django
sys.path.append('/app')  # Adjust based on your Docker setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')
django.setup()

from scanning_service.lib.data_providers import TMUServiceProvider
from scanning_service.lib.utils.logger import log


def test_tmu_provider():
    """Test the TMU service provider functionality"""
    
    # Initialize TMU provider
    # You'll need to provide a valid user_id for testing
    user_id = "test_user_id"  # Replace with actual user ID
    
    log("=" * 50)
    log("Testing TMU Service Provider")
    log("=" * 50)
    
    provider = TMUServiceProvider(user_id=user_id)
    
    # Test 1: Health Check
    log("\n=== Test 1: Health Check ===")
    is_healthy = provider.health_check()
    log(f"TMU Service Health: {'✓ Healthy' if is_healthy else '✗ Not Healthy'}")
    
    if not is_healthy:
        log("TMU service is not accessible. Please ensure:")
        log("1. The TMU service is running")
        log("2. The TMU_SERVICE_URL is correctly configured")
        log("3. Network connectivity between services is working")
        return
    
    # Test 2: Fetch Instruments
    log("\n=== Test 2: Fetch Instruments ===")
    search_params = {
        "exchange": "NSE",
        "segment": "NSE",
        "instrument_type": "EQ",
        "page_length": 10  # Just fetch 10 for testing
    }
    
    result = provider.fetch_instruments(search_params)
    
    if "error" in result.get("meta", {}):
        log(f"Error fetching instruments: {result['meta']['error']}", level="error")
    else:
        instruments = result.get("data", [])
        meta = result.get("meta", {})
        
        log(f"Successfully fetched {len(instruments)} instruments")
        log(f"Total instruments available: {meta.get('count', 'unknown')}")
        
        # Display first 3 instruments
        for i, instrument in enumerate(instruments[:3]):
            log(f"\nInstrument {i+1}:")
            log(f"  - Symbol: {instrument.get('trading_symbol')}")
            log(f"  - Name: {instrument.get('name')}")
            log(f"  - Token: {instrument.get('instrument_token')}")
            log(f"  - Exchange: {instrument.get('exchange')}")
            log(f"  - Type: {instrument.get('instrument_type')}")
    
    # Test 3: Search for specific instrument
    log("\n=== Test 3: Search for Specific Instrument ===")
    search_params = {
        "trading_symbol": "RELIANCE",
        "exchange": "NSE",
        "page_length": 5
    }
    
    result = provider.fetch_instruments(search_params)
    
    if "error" not in result.get("meta", {}):
        instruments = result.get("data", [])
        log(f"Found {len(instruments)} instruments matching 'RELIANCE'")
        
        for instrument in instruments:
            log(f"  - {instrument.get('trading_symbol')} ({instrument.get('name')})")
    
    log("\n" + "=" * 50)
    log("Test completed!")
    log("=" * 50)


if __name__ == "__main__":
    try:
        test_tmu_provider()
    except Exception as e:
        log(f"Test failed with error: {str(e)}", level="error")
        import traceback
        traceback.print_exc() 