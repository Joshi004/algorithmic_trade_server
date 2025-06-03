# Standardized Event Format for Scanning Service

## Overview

All scanner algorithms in the scanning service must emit events in a **standardized format** when publishing eligible instruments to the `initiation_queue`. This ensures consistency across different scanning algorithms and simplifies consumption by downstream services.

## Standardized Event Format

### Complete Event Structure

```json
{
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
```

### Field Specifications

| Field | Type | Required | Description | Example Values |
|-------|------|----------|-------------|----------------|
| `event_id` | string | ✅ Yes | Unique event identifier | `"evt_1734567890123_a1b2c3d4"` |
| `event_type` | string | ✅ Yes | Always `"eligible_instrument_found"` | `"eligible_instrument_found"` |
| `trade_session_id` | string | ✅ Yes | Associated trade session ID | `"session_456"` |
| `timestamp` | string | ✅ Yes | Event timestamp in IST (ISO format) | `"2024-01-15T10:30:45+05:30"` |
| `instrument_id` | string | ✅ Yes | Unique identifier for instrument | `"738561"`, `"2885"` |
| `trading_symbol` | string | ✅ Yes | Trading symbol | `"RELIANCE"`, `"HDFCBANK"` |
| `support_price` | float\|null | ❌ Optional | Support price level | `2450.50`, `null` |
| `resistance_price` | float\|null | ❌ Optional | Resistance price level | `2500.75`, `null` |
| `required_action` | string\|null | ❌ Optional | Trading action | `"buy"`, `"sell"`, `null` |
| `market_price` | float | ✅ Yes | Current market price | `2475.30` |

## Implementation Guidelines

### For Scanner Algorithm Developers

1. **Inherit from BaseScannerInterface**: All scanners must extend `BaseScannerInterface`
2. **Use the formatting method**: Call `self.format_eligible_instrument(raw_data)` before publishing
3. **Handle optional fields**: Set unsupported fields to `None` in raw data

### Example Implementation

```python
from scanning_service.lib.Algorithms.ScannerAlgos.BaseScannerInterface import BaseScannerInterface

class MyCustomScanner(BaseScannerInterface):
    def process_eligible_instrument(self, symbol, token, market_price):
        # Prepare raw instrument data
        raw_instrument_data = {
            "instrument_id": token,
            "trading_symbol": symbol,
            "support_price": self.calculate_support(symbol),  # or None if not applicable
            "resistance_price": self.calculate_resistance(symbol),  # or None if not applicable
            "required_action": self.get_action(symbol),  # "buy", "sell", or None
            "market_price": market_price
        }
        
        # Format using base class method (ensures standardization)
        instrument_data = self.format_eligible_instrument(raw_instrument_data)
        
        # Publish using event publisher
        self.event_publisher.publish_eligible_instrument(
            trade_session_id=self.trade_session_id,
            instrument_data=instrument_data,
            scanner_type="my_custom"
        )
```

## Algorithm-Specific Guidelines

### Support & Resistance Algorithms (e.g., UDTS)
- **Must provide**: `support_price`, `resistance_price`
- **Must provide**: `required_action` based on trend analysis
- **Example**: Technical analysis scanners, breakout scanners

### Volume-Based Algorithms
- **May provide**: `support_price`, `resistance_price` (if calculated)
- **Must provide**: `required_action` based on volume analysis
- **Set to null**: Fields not applicable to volume analysis

### Momentum Algorithms
- **May provide**: `support_price`, `resistance_price` (if relevant)
- **Must provide**: `required_action` based on momentum direction
- **Set to null**: Fields not calculated by momentum analysis

### Pattern Recognition Algorithms
- **May provide**: `support_price`, `resistance_price` (if pattern-based)
- **Must provide**: `required_action` based on pattern prediction
- **Set to null**: Fields not relevant to pattern analysis

## Validation Rules

### Required Fields Validation
```python
# These fields must always be present and non-null
required_fields = ['instrument_id', 'trading_symbol', 'market_price']
```

### Optional Fields Handling
```python
# These fields can be null if not applicable to the algorithm
optional_fields = ['support_price', 'resistance_price', 'required_action']
```

### Data Type Validation
- `instrument_id`: Must be convertible to string
- `trading_symbol`: Must be non-empty string
- `market_price`: Must be convertible to float and > 0
- `support_price`: Must be float or None
- `resistance_price`: Must be float or None
- `required_action`: Must be "buy", "sell", or None

## Event Publishing Flow

```
Scanner Algorithm
        ↓
Raw Instrument Data
        ↓
BaseScannerInterface.format_eligible_instrument()
        ↓
Standardized Event Data
        ↓
ScanningEventPublisher.publish_eligible_instrument()
        ↓
Redis Stream (initiation_queue)
        ↓
Initiation Service Consumer
```

## Error Handling

### Missing Required Fields
```python
ValueError: Missing required field 'instrument_id' in instrument data
```

### Invalid Data Types
```python
ValueError: market_price must be a positive number
```

### Publishing Failures
```python
# Logged but doesn't break scanner execution
log(f"Failed to publish eligible instrument: {trading_symbol}", level="warning")
```

## Testing

### Unit Test Example
```python
def test_standardized_format():
    scanner = MyCustomScanner("5minute", "user_123", "session_456")
    
    raw_data = {
        "instrument_id": "738561",
        "trading_symbol": "RELIANCE",
        "support_price": None,  # Not applicable to this algorithm
        "resistance_price": None,  # Not applicable to this algorithm
        "required_action": "buy",
        "market_price": 2475.30
    }
    
    formatted_data = scanner.format_eligible_instrument(raw_data)
    
    # Assert standardized format
    assert formatted_data["instrument_id"] == "738561"
    assert formatted_data["trading_symbol"] == "RELIANCE"
    assert formatted_data["support_price"] is None
    assert formatted_data["resistance_price"] is None
    assert formatted_data["required_action"] == "buy"
    assert formatted_data["market_price"] == 2475.30
```

## Migration Notes

### Breaking Changes
- **Old Format**: Nested `instrument` object with algorithm-specific fields
- **New Format**: Flat structure with standardized fields
- **Consumer Impact**: Initiation service consumers must update to expect new format

### Backward Compatibility
- **Not Maintained**: Old nested format is deprecated
- **Timeline**: All existing scanners updated to new format
- **Migration**: Use `BaseScannerInterface.format_eligible_instrument()` method

## Best Practices

1. **Always use the base class**: Inherit from `BaseScannerInterface`
2. **Set unused fields to None**: Don't omit optional fields, set them to `None`
3. **Validate input data**: Ensure required fields are present before formatting
4. **Handle edge cases**: Gracefully handle missing or invalid market data
5. **Log formatting errors**: Log but don't fail on formatting issues
6. **Test thoroughly**: Unit test your scanner's event format output

## Example Scanner Implementations

### UDTS Scanner (Support/Resistance)
```python
raw_instrument_data = {
    "instrument_id": token,
    "trading_symbol": symbol,
    "support_price": float(chart_data.support_level),      # ✅ Provided
    "resistance_price": float(chart_data.resistance_level), # ✅ Provided  
    "required_action": "buy" if trend == "uptrend" else "sell", # ✅ Provided
    "market_price": float(chart_data.market_price)
}
```

### Volume Scanner (Volume-based)
```python
raw_instrument_data = {
    "instrument_id": token,
    "trading_symbol": symbol,
    "support_price": None,           # ❌ Not applicable
    "resistance_price": None,        # ❌ Not applicable
    "required_action": "buy" if volume_surge else None, # ✅ Volume-based
    "market_price": float(current_price)
}
```

### Momentum Scanner (Momentum-based)
```python
raw_instrument_data = {
    "instrument_id": token,
    "trading_symbol": symbol,
    "support_price": None,           # ❌ Not calculated
    "resistance_price": None,        # ❌ Not calculated
    "required_action": "buy" if momentum > 0 else "sell", # ✅ Momentum-based
    "market_price": float(current_price)
}
```

This standardized format ensures that all scanner algorithms produce consistent, interoperable events for the initiation queue! 🚀 