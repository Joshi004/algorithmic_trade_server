# Scanning Service Implementation Status

## Overview
The scanning service has been successfully decoupled from the Trade Management Unit (TMU) and other services. It now operates as an independent microservice that communicates via APIs and message queues.

## Completed Tasks ✅

### 1. **Service Provider Architecture**
- Created `IntegrationServiceProvider` for integration service communication
- Created `TMUServiceProvider` for TMU service communication
- Removed all direct imports from TMU models
- Implemented proper error handling and logging

### 2. **Event Publishing System**
- Implemented `ScanningEventPublisher` for publishing events to Redis streams
- Created two main event streams:
  - `initiation_queue` - For publishing eligible instruments (renamed from eligible_instruments_stream)
  - `scanner_status_stream` - For publishing scanner status updates
- Added event flattening for Redis compatibility
- Implemented batch publishing capabilities
- Stream names now configurable via Django settings

### 3. **UDTS Scanner Improvements**
- Removed tight coupling with TMU models (deleted UDTSHelper)
- Added thread lifecycle management (start/stop capabilities)
- Implemented graceful shutdown
- Fixed missing `tracking_algorithm` attribute issue
- Added comprehensive event publishing in scanning loops
- Converted enums to strings for JSON serialization

### 4. **Redis Integration**
- Created Redis client utility with singleton pattern
- Added Redis configuration to Django settings
- Implemented connection pooling and health checks
- Added proper error handling and reconnection logic

### 5. **Consumer Updates**
- Updated `ScanningQueueConsumer` to handle scanner lifecycle
- Added duplicate scanner prevention
- Implemented graceful shutdown for all active scanners
- Added trade_session_id passing for event correlation

### 6. **Configuration**
- Added service URL configurations (TMU_SERVICE_URL, INTEGRATION_SERVICE_URL, SCANNING_SERVICE_URL)
- Added comprehensive Redis configuration settings with timeouts and connection parameters
- Added consumer configuration parameters (batch size, timeout)
- Added service communication timeout settings
- Made all configurations environment-variable based with proper fallbacks
- Stream names now configurable via REDIS_STREAM_* environment variables
- All configuration parameters consistent across Docker Compose and application settings

### 7. **Test Scripts**
- Created `test_tmu_provider.py` for TMU service testing
- Created `test_integration_provider.py` for integration service testing
- Created `test_event_publisher.py` for event publishing testing

## Remaining Tasks 📋

### 1. **Authentication Between Services**
- Implement JWT token passing between services
- Add service-to-service authentication
- Handle token refresh for long-running scanners

### 2. **Distributed Locking**
- Implement Redis-based distributed locks for scanner coordination
- Prevent duplicate scanners across multiple containers
- Add lock expiry and renewal mechanisms

### 3. **Consumer Group for Initiation Queue**
- Create a consumer for the `initiation_queue` stream (renamed from eligible_instruments_stream)
- This consumer should trigger tracking algorithms
- Handle event acknowledgment and retries

### 4. **Monitoring and Health Checks**
- Implement scanner health monitoring
- Add metrics collection (scan duration, instruments processed, etc.)
- Create dashboards for monitoring scanner performance

### 5. **Error Recovery**
- Implement circuit breaker pattern for API calls
- Add retry logic with exponential backoff
- Handle service unavailability gracefully

### 6. **Performance Optimization**
- Implement connection pooling for API calls
- Add caching for frequently accessed instrument data
- Optimize scanning loops for large instrument sets

### 7. **Documentation**
- Document event formats and schemas
- Create API documentation for service providers
- Add deployment guides

## Event Formats

### Eligible Instrument Event (Standardized Format)
```json
{
  "event_id": "evt_1234567890_abcd1234",
  "event_type": "eligible_instrument_found",
  "trade_session_id": "session_456",
  "timestamp": "2024-01-15T10:30:45+05:30",
  "instrument_id": "738561",
  "trading_symbol": "RELIANCE",
  "support_price": 2450.50,
  "resistance_price": 2500.75,
  "required_action": "buy",
  "market_price": 2475.30,
  "scanning_algorithm_id": 1,
  "initiation_algorithm_id": 2,
  "termination_algorithm_id": 3
}
```

**Field Descriptions:**
- `event_id`: Unique event identifier (format: `evt_<timestamp>_<uuid>`)
- `event_type`: Always `"eligible_instrument_found"` for eligible instruments
- `trade_session_id`: Associated trade session ID for correlation
- `timestamp`: Event timestamp in IST (ISO format)
- `instrument_id`: Unique identifier for the instrument (string)
- `trading_symbol`: Trading symbol like "RELIANCE", "HDFCBANK" (string)
- `support_price`: Support price level or `null` if not applicable (float|null)
- `resistance_price`: Resistance price level or `null` if not applicable (float|null)
- `required_action`: `"buy"`, `"sell"`, or `null` based on analysis (string|null)
- `market_price`: Current market price (float)
- `scanning_algorithm_id`: ID of the scanning algorithm used (integer)
- `initiation_algorithm_id`: ID of the initiation algorithm for the session (integer)
- `termination_algorithm_id`: ID of the termination algorithm for the session (integer)

**Note:** This standardized format must be followed by all scanner algorithms. Fields not applicable to a specific algorithm should be set to `null`.

### Scanner Status Event
```json
{
  "event_id": "evt_1234567890_efgh5678",
  "event_type": "scanner_status_update",
  "user_id": "user_123",
  "trade_session_id": "session_456",
  "scanner_type": "udts",
  "status": "running",
  "timestamp": "2024-01-15T10:30:45+05:30",
  "details": {
    "scan_cycle": 5,
    "instruments_scanned": 250,
    "eligible_found": 12,
    "scan_duration_seconds": 45.2
  }
}
```

## Usage Example

### Starting a Scanner (New Pattern)
```python
from scanning_service.lib.data_providers import IntegrationServiceProvider, TMUServiceProvider
from scanning_service.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory

# Create factory
factory = ScannerAlgoFactory()

# Create scanner instance (bare, unconfigured)
scanner = factory.get_scanner(scanning_algo_name="udts")

# Configure the scanner with required parameters
scanner.configure(
    trade_freq="5minute",
    user_id="user_123",
    trade_session_id="session_456"
)

# Alternatively, provide custom providers
integration_provider = IntegrationServiceProvider(user_id="user_123")
tmu_provider = TMUServiceProvider(user_id="user_123")

scanner.configure(
    trade_freq="5minute",
    user_id="user_123",
    trade_session_id="session_456",
    integration_provider=integration_provider,
    tmu_provider=tmu_provider
)

# Start scanning
scanner.fetch_instrument_tokens_and_start_tracking("user_123", is_dummy=False)

# Stop scanning when done
scanner.stop_scanning()
```

### Factory Benefits (New Pattern)
- **Minimal Factory**: Factory only needs algorithm name
- **Flexible Configuration**: Each scanner can accept different configuration
- **Lazy Loading**: Dependencies imported only when needed
- **Easy Extension**: Add new scanners without changing factory signature

## Testing

1. **Test TMU Service Provider**:
   ```bash
   python algorithmic_trade_server/scanning_service/test_tmu_provider.py
   ```

2. **Test Integration Service Provider**:
   ```bash
   python algorithmic_trade_server/scanning_service/test_integration_provider.py
   ```

3. **Test Event Publisher**:
   ```bash
   python algorithmic_trade_server/scanning_service/test_event_publisher.py
   ```

## Notes

- All services must be running for full functionality
- Redis must be accessible for event publishing
- Ensure proper network connectivity between services
- Monitor Redis memory usage as streams can grow large 