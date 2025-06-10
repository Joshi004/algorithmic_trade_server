#!/usr/bin/env python
"""
Test script for the scanning service event publisher.
Run this to verify that events are being published correctly to Redis streams.
"""
import os
import sys
import django

# Setup Django
sys.path.append('/app')  # Adjust based on your Docker setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')
django.setup()

from scanning_service.lib.utils.redis import get_scanning_event_publisher, get_publisher_client
from scanning_service.lib.utils.logger import log
import time


def test_event_publisher():
    """Test the event publisher functionality"""
    
    log("=" * 50)
    log("Testing Scanning Service Event Publisher")
    log("=" * 50)
    
    # Get event publisher
    publisher = get_scanning_event_publisher()
    
    # Test data
    trade_session_id = "session_456"
    
    # Test 1: Publish eligible instrument event
    log("\n=== Test 1: Publish Eligible Instrument Event ===")
    
    instrument_data = {
        "instrument_id": "738561",
        "trading_symbol": "RELIANCE",
        "support_price": 2450.50,
        "resistance_price": 2500.75,
        "required_action": "buy",
        "market_price": 2475.30
    }
    
    message_id = publisher.publish_eligible_instrument(
        trade_session_id=trade_session_id,
        instrument_data=instrument_data,
        scanning_algorithm_id=1,
        initiation_algorithm_id=1,
        termination_algorithm_id=1
    )
    
    if message_id:
        log(f"✅ Successfully published eligible instrument event: {message_id}")
    else:
        log("❌ Failed to publish eligible instrument event")
    
    # Test 2: Publish scanner status events
    log("\n=== Test 2: Publish Scanner Status Events ===")
    
    # Scanner started
    status_id = publisher.publish_scanner_status(
        user_id="test_user_123",
        trade_session_id=trade_session_id,
        scanner_type="udts",
        status="started",
        details={"trade_frequency": "5-minute", "instruments_count": 100}
    )
    
    if status_id:
        log(f"✅ Published scanner started event: {status_id}")
    
    time.sleep(1)
    
    # Scanner running
    status_id = publisher.publish_scanner_status(
        user_id="test_user_123",
        trade_session_id=trade_session_id,
        scanner_type="udts",
        status="running",
        details={
            "scan_cycle": 1,
            "instruments_scanned": 50,
            "eligible_found": 3,
            "scan_duration_seconds": 45.2
        }
    )
    
    if status_id:
        log(f"✅ Published scanner running event: {status_id}")
    
    # Test 3: Publish batch eligible instruments
    log("\n=== Test 3: Publish Batch Eligible Instruments ===")
    
    instruments = [
        {
            "instrument_id": "2885",
            "trading_symbol": "HDFCBANK",
            "support_price": 1650.00,
            "resistance_price": 1680.00,
            "required_action": "buy",
            "market_price": 1665.50
        },
        {
            "instrument_id": "3045",
            "trading_symbol": "SBIN",
            "support_price": 620.00,
            "resistance_price": 635.00,
            "required_action": "sell",
            "market_price": 627.75
        }
    ]
    
    published_count = publisher.publish_batch_eligible_instruments(
        trade_session_id=trade_session_id,
        instruments=instruments,
        scanning_algorithm_id=1,
        initiation_algorithm_id=1,
        termination_algorithm_id=1
    )
    
    log(f"✅ Published {published_count} instruments in batch")
    
    # Test 4: Verify events in Redis
    log("\n=== Test 4: Verify Events in Redis Streams ===")
    
    try:
        publisher_client = get_publisher_client()
        
        # Check initiation queue stream (renamed from eligible_instruments_stream)
        stream_info = publisher_client.get_stream_info('initiation_queue')
        log(f"Initiation queue stream - Length: {stream_info.get('length', 0)}")
        
        # Check scanner status stream
        stream_info = publisher_client.get_stream_info('scanner_status_stream')
        log(f"\nScanner status stream - Length: {stream_info.get('length', 0)}")
        
    except Exception as e:
        log(f"Error checking Redis streams: {str(e)}", level="error")
    
    log("\n" + "=" * 50)
    log("Event Publisher test completed!")
    log("=" * 50)


if __name__ == "__main__":
    try:
        test_event_publisher()
    except Exception as e:
        log(f"Test failed with error: {str(e)}", level="error")
        import traceback
        traceback.print_exc() 