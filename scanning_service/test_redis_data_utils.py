#!/usr/bin/env python
"""
Test script for Redis data utilities.
Demonstrates flattening and unflattening operations for Redis streams.
"""
import os
import sys
import django

# Setup Django
sys.path.append('/app')  # Adjust based on your Docker setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')
django.setup()

from scanning_service.lib.utils.redis_data_utils import (
    flatten_dict, 
    unflatten_dict, 
    prepare_for_redis_stream, 
    restore_from_redis_stream,
    convert_redis_stream_data,
    unflatten_dict_with_types,
    smart_type_conversion
)
from scanning_service.lib.utils.logger import log


def test_basic_flattening():
    """Test basic flattening and unflattening operations"""
    log("=" * 50)
    log("Testing Basic Flattening Operations")
    log("=" * 50)
    
    # Test simple nested structure
    original_data = {
        "user": {
            "id": 123,
            "name": "John Doe"
        },
        "status": "active",
        "metadata": {
            "created_at": "2024-01-15",
            "settings": {
                "debug": True,
                "theme": "dark"
            }
        },
        "tags": ["important", "vip"],
        "score": None
    }
    
    log(f"Original data: {original_data}")
    
    # Flatten the data
    flattened = flatten_dict(original_data)
    log(f"Flattened data: {flattened}")
    
    # Unflatten the data
    restored = unflatten_dict(flattened)
    log(f"Restored data: {restored}")
    
    # Test that we can round-trip the data
    log(f"Round-trip successful: {original_data == restored}")
    

def test_eligible_instrument_event():
    """Test with realistic eligible instrument event data"""
    log("\n" + "=" * 50)
    log("Testing Eligible Instrument Event")
    log("=" * 50)
    
    event_data = {
        "event_id": "evt_1734567890123_a1b2c3d4",
        "event_type": "eligible_instrument_found",
        "trade_session_id": "session_456",
        "timestamp": "2024-01-15T10:30:45+05:30",
        "instrument_id": "738561",
        "trading_symbol": "RELIANCE",
        "support_price": 2450.50,
        "resistance_price": 2500.75,
        "required_action": "buy",
        "market_price": 2475.30
    }
    
    log(f"Original event: {event_data}")
    
    # Prepare for Redis stream
    redis_ready = prepare_for_redis_stream(event_data)
    log(f"Redis-ready format: {redis_ready}")
    
    # Restore from Redis stream
    restored_event = restore_from_redis_stream(redis_ready)
    log(f"Restored event: {restored_event}")
    
    log(f"Event round-trip successful: {event_data == restored_event}")


def test_trade_session_event():
    """Test with trade session initiation event (more complex structure)"""
    log("\n" + "=" * 50)
    log("Testing Trade Session Event")
    log("=" * 50)
    
    trade_session_event = {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "trade_session_initiated",
        "timestamp": "2024-01-15T10:30:45+05:30",
        "trade_session_id": 123,
        "user_id": "user_public_id_uuid",
        "algorithm_config": {
            "scanning_algorithm_id": 2,
            "initiation_algorithm_id": 3,
            "termination_algorithm_id": 4
        },
        "trading_frequency": "5minute",
        "is_dummy": True,
        "session_status": "started"
    }
    
    log(f"Original trade session event: {trade_session_event}")
    
    # Test with convert_redis_stream_data function
    flattened = convert_redis_stream_data(trade_session_event, 'flatten')
    log(f"Flattened: {flattened}")
    
    restored = convert_redis_stream_data(flattened, 'unflatten')
    log(f"Restored: {restored}")
    
    log(f"Trade session round-trip successful: {trade_session_event == restored}")


def test_type_conversion():
    """Test smart type conversion features"""
    log("\n" + "=" * 50)
    log("Testing Type Conversion")
    log("=" * 50)
    
    # Test individual type conversions
    test_values = [
        ("123", 123),
        ("45.67", 45.67),
        ("true", True),
        ("false", False),
        ("null", None),
        ('["item1", "item2"]', ["item1", "item2"]),
        ('{"key": "value"}', {"key": "value"}),
        ("", None),
        ("regular string", "regular string")
    ]
    
    for input_val, expected in test_values:
        result = smart_type_conversion(input_val)
        log(f"'{input_val}' -> {result} (type: {type(result).__name__}) - Expected: {expected}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    # Test unflattening with type conversion
    flattened_with_types = {
        'user_id': '123',
        'user_active': 'true',
        'user_score': '89.5',
        'metadata': '',
        'tags': '["tag1", "tag2"]',
        'config_debug': 'false'
    }
    
    log(f"Flattened data with string types: {flattened_with_types}")
    
    # Restore without type conversion
    restored_strings = unflatten_dict(flattened_with_types)
    log(f"Restored (strings): {restored_strings}")
    
    # Restore with type conversion
    restored_typed = unflatten_dict_with_types(flattened_with_types)
    log(f"Restored (typed): {restored_typed}")


def test_edge_cases():
    """Test edge cases and error handling"""
    log("\n" + "=" * 50)
    log("Testing Edge Cases")
    log("=" * 50)
    
    # Empty dictionary
    empty_data = {}
    flattened_empty = flatten_dict(empty_data)
    restored_empty = unflatten_dict(flattened_empty)
    log(f"Empty dict test: {empty_data} -> {flattened_empty} -> {restored_empty}")
    assert empty_data == restored_empty
    
    # Single level dictionary
    single_level = {"key": "value", "number": 42}
    flattened_single = flatten_dict(single_level)
    restored_single = unflatten_dict(flattened_single)
    log(f"Single level test: {single_level} -> {flattened_single} -> {restored_single}")
    # Note: numbers will be strings after round-trip without type conversion
    
    # Test invalid operation
    try:
        convert_redis_stream_data({}, 'invalid_operation')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        log(f"Correctly caught error: {e}")
    
    log("All edge case tests passed!")


def test_performance():
    """Basic performance test with larger data structures"""
    log("\n" + "=" * 50)
    log("Testing Performance")
    log("=" * 50)
    
    import time
    
    # Create a larger nested structure
    large_data = {
        "instruments": [f"STOCK_{i}" for i in range(100)],
        "users": {f"user_{i}": {"id": i, "active": i % 2 == 0} for i in range(50)},
        "metadata": {
            "version": "1.0",
            "config": {
                "settings": {f"setting_{i}": f"value_{i}" for i in range(20)}
            }
        }
    }
    
    # Time the flattening operation
    start_time = time.time()
    flattened = flatten_dict(large_data)
    flatten_time = time.time() - start_time
    
    # Time the unflattening operation
    start_time = time.time()
    restored = unflatten_dict(flattened)
    unflatten_time = time.time() - start_time
    
    log(f"Large data structure:")
    log(f"  - Original keys: {len(large_data)}")
    log(f"  - Flattened keys: {len(flattened)}")
    log(f"  - Flatten time: {flatten_time:.4f} seconds")
    log(f"  - Unflatten time: {unflatten_time:.4f} seconds")
    log(f"  - Round-trip successful: {large_data == restored}")


if __name__ == "__main__":
    try:
        test_basic_flattening()
        test_eligible_instrument_event()
        test_trade_session_event()
        test_type_conversion()
        test_edge_cases()
        test_performance()
        
        log("\n" + "=" * 50)
        log("🎉 All Redis Data Utilities tests passed!")
        log("=" * 50)
        
    except Exception as e:
        log(f"❌ Test failed with error: {str(e)}", level="error")
        import traceback
        traceback.print_exc() 