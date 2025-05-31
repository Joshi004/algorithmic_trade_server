# Redis Stream Integration - Phase 1 Implementation

## Overview

This document describes the Phase 1 implementation of Redis Stream integration for Trade Session events. When new trade sessions are created, events are automatically published to a Redis stream named `initiation_queue` for further processing by consumer services.

## Architecture

### Components

1. **Redis Stream Client** (`trade_management_unit/lib/common/Utils/redis_stream_client.py`)
   - Handles Redis connections and stream operations
   - Provides fire-and-forget publishing with comprehensive error handling
   - Uses environment variables for configuration

2. **Event Publisher** (`trade_management_unit/lib/common/event_publisher.py`)
   - Formats trade session events into standardized structure
   - Publishes events to Redis streams
   - Integrates with existing logging system

3. **Trade Session Model Integration** (`trade_management_unit/models/TradeSession.py`)
   - Modified to publish events when new sessions are created
   - Graceful error handling - Redis failures don't break API functionality

4. **Trade Session API** (`trade_management_unit/views/trade_session_view.py`)
   - Updated to properly handle both new and existing trade sessions
   - Returns appropriate responses for both scenarios

## Event Structure

Events published to the `initiation_queue` stream have the following structure:

```json
{
  "event_id": "uuid4_string",
  "event_type": "trade_session_initiated",
  "timestamp": "2024-01-01T10:00:00+05:30",
  "trade_session_id": 123,
  "user_id": "user_uuid_string",
  "algorithm_config": {
    "scanning_algorithm_id": 2,
    "initiation_algorithm_id": 3,
    "termination_algorithm_id": 4
  },
  "trading_frequency": "5minute",
  "is_dummy": true,
  "session_status": "started",
  "started_at": "2024-01-01T10:00:00+05:30"
}
```

## Configuration

### Environment Variables

The Redis connection uses the following environment variables (already configured in docker-compose.yml):

- `REDIS_HOST`: Redis server hostname (default: `ats-redis`)
- `REDIS_PORT`: Redis server port (default: `6379`)

### Dependencies

Added `redis==4.5.4` to `requirements.txt` for direct Redis operations.

## Usage

### Automatic Event Publishing

Events are automatically published when new trade sessions are created via:

1. **API Endpoint**: `POST /tmu/initiate_trade_session/`
2. **Model Method**: `TradeSession.fetch_or_create_trade_session()`
3. **Model Method**: `TradeSession.create_trade_session()`

### API Response Format

The API now returns enhanced responses for better frontend handling:

**New Session Created:**
```json
{
  "trade_session_id": 123,
  "message": "New session created",
  "status": "new"
}
```

**Existing Session Found:**
```json
{
  "trade_session_id": 123,
  "message": "Session already exists",
  "status": "existing"
}
```

### Manual Event Publishing

```python
from trade_management_unit.lib.common.event_publisher import get_trade_session_event_publisher

# Get the event publisher
publisher = get_trade_session_event_publisher()

# Publish an event (typically done automatically)
success = publisher.publish_trade_session_initiated(trade_session_obj, "New session created")
```

### Health Checks

```python
from trade_management_unit.lib.common.Utils.redis_stream_client import get_redis_stream_client

# Check Redis connection health
redis_client = get_redis_stream_client()
is_healthy = redis_client.health_check()
```

## Testing

### Running Tests

A comprehensive test suite is available to verify the integration:

```bash
cd algorithmic_trade_server
python trade_management_unit/tests/test_redis_stream_integration.py
```

### API Testing

Test the API behavior for both new and existing sessions:

```bash
cd algorithmic_trade_server
python test_trade_session_api.py
```

### Test Coverage

The test suite covers:
- Redis connection health
- Stream publishing functionality
- Event formatting and structure
- Integration with mock data
- Error handling scenarios
- API response for new and existing sessions

## Error Handling

### Graceful Degradation

- **Redis Unavailable**: Events are logged but API continues to function normally
- **Stream Publish Failure**: Errors are logged with full context
- **Connection Timeout**: 5-second timeout with proper error logging
- **Event Formatting Errors**: Detailed error logging with context
- **Existing Sessions**: Returns 200 success with appropriate message instead of error

### Logging

All Redis-related events and errors are logged using the existing custom logger:

```python
from trade_management_unit.lib.common.Utils.custome_logger import log

# Success logging
log(f"Successfully published event to stream 'initiation_queue' with ID: {stream_id}")

# Error logging
log(f"Redis connection error while publishing to stream: {str(e)}", level="error")
```

## API Impact

### Existing Functionality

✅ **No Breaking Changes**: All existing API endpoints continue to work unchanged

### New Behavior

- **New Trade Sessions**: Events are published to `initiation_queue` Redis stream
- **Existing Sessions**: Returns 200 success with "Session already exists" message
- **Enhanced Response**: API now includes status and message fields for better frontend handling
- **Error Scenarios**: API responses remain unchanged even if Redis publishing fails

### API Examples

**Creating a new session:**
```bash
GET /tmu/initiate_trade_session/?trading_frequency=5minute&dummy=1&scanning_algorithm_id=2&initiation_algorithm_id=3&termination_algorithm_id=4
```

**Response (first call):**
```json
{
  "trade_session_id": 123,
  "message": "New session created",
  "status": "new"
}
```

**Response (subsequent calls with same parameters):**
```json
{
  "trade_session_id": 123,
  "message": "Session already exists", 
  "status": "existing"
}
```

## Stream Name

- **Stream Name**: `initiation_queue`
- **Event Type**: `trade_session_initiated`
- **Format**: Redis Stream (XADD command)

## Next Steps (Phase 2)

This Phase 1 implementation provides the foundation for:

1. **Consumer Services**: Services that read from `initiation_queue` and process events
2. **Acknowledgment System**: Proper message acknowledgment and retry logic
3. **Dead Letter Queue**: Handling of failed message processing
4. **Monitoring**: Dashboards for queue health and processing metrics
5. **Scaling**: Multiple consumer groups for parallel processing

## Monitoring

### Redis CLI Commands

Monitor the stream using Redis CLI:

```bash
# Connect to Redis container
docker exec -it ats-redis-server redis-cli

# View stream info
XINFO STREAM initiation_queue

# Read latest events
XREAD STREAMS initiation_queue $

# Read all events
XRANGE initiation_queue - +
```

### Application Logs

Monitor application logs for Redis-related events:

```bash
# View logs
docker-compose logs -f ats-app | grep -i redis
```

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Verify Redis container is running: `docker-compose ps`
   - Check network connectivity: `docker-compose exec ats-app ping ats-redis`

2. **Events Not Published**
   - Check application logs for Redis errors
   - Verify environment variables are set correctly
   - Run the test suite to identify issues

3. **Stream Not Created**
   - Streams are created automatically on first publish
   - Verify Redis permissions and configuration

4. **API Returns 400 for Existing Sessions**
   - This issue has been fixed - API now returns 200 for existing sessions
   - Ensure you're using the updated view code

### Debug Mode

Enable detailed logging by checking the log files:

```bash
# View application logs
tail -f algorithmic_trade_server/logfile.log | grep -i redis
```

## Security Considerations

- Redis connection uses default authentication (none) in development
- For production, consider:
  - Redis authentication (AUTH command)
  - TLS encryption for Redis connections
  - Network isolation and firewall rules
  - Rate limiting on Redis operations 