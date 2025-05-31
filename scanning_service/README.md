# Scanning Service

## Overview

The `scanning_service` is a Django app designed to consume and process trade session scanning events from the Redis stream `scanning_queue`. This service runs as part of the main Django application alongside the `trade_management_unit` and `integration_service`.

## Purpose

When new trade sessions are created via the API `/tmu/initiate_trade_session`, events are published to the `scanning_queue` Redis stream. This service consumes those events and processes them accordingly.

## Architecture

### Components

1. **ScanningQueueConsumer** (`consumers/scanning_queue_consumer.py`)
   - Redis stream consumer that reads from `scanning_queue`
   - Processes `trade_session_initiated` events
   - Uses consumer groups for scalable message processing
   - Handles message acknowledgment and error recovery

2. **Management Command** (`management/commands/start_scanning_service.py`)
   - Django management command to start the service
   - Supports graceful shutdown with signal handling
   - Includes health check functionality

3. **Logger Utility** (`lib/utils/logger.py`)
   - Simple logging utility for the service
   - Provides timestamped logging with different levels

## Running the Service

### As Part of the Main Application

The scanning service is a Django app that runs within the main `ats-app` container. You can start the service in several ways:

### Manual Execution

Run the service manually within the Django container:

```bash
# Run the service
docker-compose exec ats-app python manage.py start_scanning_service

# Run with verbose logging
docker-compose exec ats-app python manage.py start_scanning_service --verbose

# Run health check only
docker-compose exec ats-app python manage.py start_scanning_service --health-check
```

### Background Execution

You can also run it in the background:

```bash
# Run in background within the container
docker-compose exec -d ats-app python manage.py start_scanning_service --verbose
```

### Development Mode

For development, you might want to run it in a separate terminal for better monitoring:

```bash
# Open a new shell in the container
docker-compose exec ats-app bash

# Then run the service
python manage.py start_scanning_service --verbose
```

## Event Processing

### Supported Events

The service currently processes events of type `trade_session_initiated` with the following structure:

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

### Current Processing Logic

For now, the service implements basic event processing:

1. **Event Validation**: Verifies the event type is `trade_session_initiated`
2. **Data Extraction**: Extracts key information from the event
3. **Logging**: Logs event details for monitoring and debugging
4. **Acknowledgment**: Acknowledges successfully processed messages

### Future Enhancements

The service is designed to be extensible. Future enhancements might include:

- Integration with algorithm execution systems
- Trade session state management
- Error handling and retry logic
- Dead letter queue for failed messages
- Metrics and monitoring

## Configuration

### Environment Variables

The service uses the same environment variables as the main application:

- `REDIS_HOST`: Redis server hostname (default: `ats-redis`)
- `REDIS_PORT`: Redis server port (default: `6379`)
- `DATABASE_*`: Database connection settings (for Django ORM access if needed)

### Consumer Configuration

The service is configured with the following defaults:

- **Stream Name**: `scanning_queue`
- **Consumer Group**: `scanning_service_group`
- **Batch Size**: 10 messages per read
- **Timeout**: 1 second for blocking reads

## Monitoring

### Logs

The service logs all activities to both the Django logging system and console output. Key log messages include:

- Service startup and shutdown
- Event processing details
- Error messages and connection issues
- Health check results

### Health Checks

Check the service health:

```bash
docker-compose exec ats-app python manage.py start_scanning_service --health-check
```

### Redis Stream Monitoring

Monitor the `scanning_queue` stream directly:

```bash
# Connect to Redis
docker exec -it ats-redis-server redis-cli

# Check stream info
XINFO STREAM scanning_queue

# View consumer group info
XINFO GROUPS scanning_queue

# View pending messages
XPENDING scanning_queue scanning_service_group
```

## Development

### Testing Events

You can test the service by creating trade sessions via the API:

```bash
curl "http://localhost:18000/tmu/initiate_trade_session/?trading_frequency=3minute&dummy=1&scanning_algorithm_id=2&initiation_algorithm_id=1&termination_algorithm_id=1"
```

This will create an event in the `scanning_queue` that the service will process.

### Testing the Service

1. Start the service in one terminal:
```bash
docker-compose exec ats-app python manage.py start_scanning_service --verbose
```

2. In another terminal, create a trade session:
```bash
curl "http://localhost:18000/tmu/initiate_trade_session/?trading_frequency=3minute&dummy=1&scanning_algorithm_id=2&initiation_algorithm_id=1&termination_algorithm_id=1"
```

3. You should see the service processing the event in the first terminal.

### Extending the Service

To add new processing logic:

1. Modify the `_process_event` method in `ScanningQueueConsumer`
2. Add any required Django models to `models.py`
3. Create additional utility functions in the `lib` directory
4. Add comprehensive logging for new functionality

## Integration with Main Application

The scanning service is fully integrated with the main Django application:

- **Django App**: Registered in `INSTALLED_APPS` as `scanning_service`
- **Database Access**: Has access to all Django models and ORM functionality
- **Settings**: Uses the same Django settings as the main application
- **Logging**: Integrates with the main application's logging system
- **Redis**: Shares the same Redis instance as other services

## Error Handling

The service implements comprehensive error handling:

- **Connection Errors**: Automatic retry with exponential backoff
- **Processing Errors**: Messages are not acknowledged and remain in the stream
- **Graceful Shutdown**: Responds to SIGINT and SIGTERM signals
- **Health Monitoring**: Built-in health check functionality

## Dependencies

The service requires:

- Redis (for stream consumption)
- Django (for management command framework)
- Python `redis` library (for direct Redis operations)

All dependencies are included in the main application's `requirements.txt`. 