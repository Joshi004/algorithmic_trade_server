#!/usr/bin/env python
"""
Test script for the new Redis utilities structure.
Demonstrates the organized approach with separate publisher and consumer clients.
"""
import os
import sys
import django
import time

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')
django.setup()

from scanning_service.lib.utils.logger import log
from scanning_service.lib.utils.redis import (
    get_redis_config,
    get_publisher_client,
    get_scanning_event_publisher,
    create_consumer_client,
    prepare_for_redis_stream,
    restore_from_redis_stream
)


def test_redis_config():
    """Test Redis configuration management"""
    log("=" * 60)
    log("Testing Redis Configuration")
    log("=" * 60)
    
    config = get_redis_config()
    config.log_config()
    
    # Test different client configurations
    pub_config = config.get_publisher_config()
    consumer_config = config.get_consumer_config()
    
    log(f"Publisher pool size: {pub_config.get('connection_pool_kwargs', {}).get('max_connections', 'default')}")
    log(f"Consumer pool size: {consumer_config.get('connection_pool_kwargs', {}).get('max_connections', 'default')}")
    
    return True


def test_publisher_client():
    """Test the publisher Redis client"""
    log("\n" + "=" * 60)
    log("Testing Publisher Client")
    log("=" * 60)
    
    # Get publisher client (singleton)
    publisher = get_publisher_client()
    
    # Test health check
    if publisher.health_check():
        log("✅ Publisher client health check passed")
    else:
        log("❌ Publisher client health check failed")
        return False
    
    # Test publishing to a test stream
    test_data = {
        "test_id": "test_123",
        "message": "Hello from publisher",
        "timestamp": time.time(),
        "nested": {
            "key1": "value1",
            "key2": 42
        }
    }
    
    # Flatten for Redis
    flat_data = prepare_for_redis_stream(test_data)
    log(f"Flattened data: {flat_data}")
    
    # Publish to test stream
    message_id = publisher.publish_to_stream("test_publisher_stream", flat_data)
    if message_id:
        log(f"✅ Published test message with ID: {message_id}")
    else:
        log("❌ Failed to publish test message")
        return False
    
    # Test stream info
    stream_info = publisher.get_stream_info("test_publisher_stream")
    log(f"Stream info: {stream_info}")
    
    return True


def test_consumer_client():
    """Test the consumer Redis client"""
    log("\n" + "=" * 60)
    log("Testing Consumer Client")
    log("=" * 60)
    
    # Create consumer client (separate instance)
    consumer = create_consumer_client("test_consumer_group", "test_consumer_1")
    
    # Test health check
    if consumer.health_check():
        log("✅ Consumer client health check passed")
    else:
        log("❌ Consumer client health check failed")
        return False
    
    # Ensure consumer group exists
    if consumer.ensure_consumer_group("test_publisher_stream"):
        log("✅ Consumer group created/verified")
    else:
        log("❌ Failed to create consumer group")
        return False
    
    # Try to read messages (non-blocking)
    messages = consumer.read_from_stream("test_publisher_stream", count=5, block=100)  # 100ms timeout
    
    if messages:
        log(f"✅ Read {len(messages)} stream(s) with messages")
        for stream_name, stream_messages in messages:
            log(f"Stream: {stream_name}")
            for message_id, fields in stream_messages:
                # Restore from Redis format
                restored_data = restore_from_redis_stream(fields)
                log(f"  Message {message_id}: {restored_data}")
                
                # Acknowledge the message
                if consumer.acknowledge_message("test_publisher_stream", message_id):
                    log(f"  ✅ Acknowledged message {message_id}")
    else:
        log("No messages available (or timeout)")
    
    return True


def test_event_publisher():
    """Test the scanning event publisher"""
    log("\n" + "=" * 60)
    log("Testing Scanning Event Publisher")
    log("=" * 60)
    
    # Get event publisher (singleton)
    event_publisher = get_scanning_event_publisher()
    
    # Test publishing eligible instrument
    instrument_data = {
        "instrument_id": "738561",
        "trading_symbol": "RELIANCE",
        "support_price": 2450.50,
        "resistance_price": 2500.75,
        "required_action": "buy",
        "market_price": 2475.30
    }
    
    message_id = event_publisher.publish_eligible_instrument(
        trade_session_id="session_123",
        instrument_data=instrument_data,
        scanner_type="udts"
    )
    
    if message_id:
        log(f"✅ Published eligible instrument event: {message_id}")
    else:
        log("❌ Failed to publish eligible instrument event")
        return False
    
    # Test publishing scanner status
    message_id = event_publisher.publish_scanner_status(
        user_id="user_456",
        trade_session_id="session_123",
        scanner_type="udts",
        status="running",
        details={"instruments_scanned": 50, "eligible_found": 3}
    )
    
    if message_id:
        log(f"✅ Published scanner status event: {message_id}")
    else:
        log("❌ Failed to publish scanner status event")
        return False
    
    # Test batch publishing
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
    
    published_count = event_publisher.publish_batch_eligible_instruments(
        trade_session_id="session_123",
        instruments=instruments,
        scanner_type="udts"
    )
    
    log(f"✅ Published {published_count}/{len(instruments)} instruments in batch")
    
    # Get stream status
    stream_status = event_publisher.get_stream_status()
    log(f"Stream status: {stream_status}")
    
    return True


def test_data_utilities():
    """Test data flattening and unflattening utilities"""
    log("\n" + "=" * 60)
    log("Testing Data Utilities")
    log("=" * 60)
    
    # Test complex nested data
    original_data = {
        "event_id": "evt_123",
        "user": {
            "id": 456,
            "profile": {
                "name": "John Doe",
                "active": True
            }
        },
        "tags": ["scanner", "udts"],
        "metadata": None,
        "score": 98.5
    }
    
    log(f"Original data: {original_data}")
    
    # Flatten for Redis
    flattened = prepare_for_redis_stream(original_data)
    log(f"Flattened: {flattened}")
    
    # Restore from Redis
    restored = restore_from_redis_stream(flattened)
    log(f"Restored: {restored}")
    
    # Check if structure is preserved
    if restored["event_id"] == original_data["event_id"] and restored["user"]["id"] == str(original_data["user"]["id"]):
        log("✅ Data structure preserved through flatten/unflatten cycle")
        return True
    else:
        log("❌ Data structure not preserved")
        return False


def main():
    """Run all tests"""
    log("🚀 Starting Redis utilities structure tests...")
    
    tests = [
        ("Redis Configuration", test_redis_config),
        ("Publisher Client", test_publisher_client),
        ("Consumer Client", test_consumer_client),
        ("Event Publisher", test_event_publisher),
        ("Data Utilities", test_data_utilities)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            log(f"❌ Test '{test_name}' failed with exception: {str(e)}", level="error")
            results.append((test_name, False))
    
    # Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        log(f"{test_name}: {status}")
        if result:
            passed += 1
    
    log(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        log("🎉 All tests passed! Redis utilities structure is working correctly.")
    else:
        log("⚠️  Some tests failed. Check the logs above for details.")


if __name__ == "__main__":
    main() 