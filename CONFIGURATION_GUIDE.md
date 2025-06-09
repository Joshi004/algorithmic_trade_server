# ATS Configuration Guide

This document outlines all configuration parameters used across the Algorithmic Trading System (ATS) services.

## Environment Variables

All configuration parameters are environment variables with sensible defaults. These can be set in Docker Compose, Kubernetes, or any deployment environment.

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_ENGINE` | `django.db.backends.mysql` | Django database backend |
| `DATABASE_NAME` | `ats_db` | Database name |
| `DATABASE_USER` | `ats_user` | Database username |
| `DATABASE_PASSWORD` | `ats_password` | Database password |
| `DATABASE_HOST` | `ats-db` | Database host |
| `DATABASE_PORT` | `3306` | Database port |
| `TEST_DATABASE_NAME` | `test_ats_db` | Test database name |

### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_SOCKET_TIMEOUT` | `5` | Socket timeout in seconds |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | `5` | Connection timeout in seconds |
| `REDIS_HEALTH_CHECK_INTERVAL` | `30` | Health check interval in seconds |

### Redis Streams Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_STREAM_SCANNING_QUEUE` | `scanning_queue` | Stream for trade session events |
| `REDIS_STREAM_INITIATION_QUEUE` | `initiation_queue` | Stream for eligible instruments |
| `REDIS_STREAM_SCANNER_STATUS` | `scanner_status_stream` | Stream for scanner status updates |

### Consumer Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_CONSUMER_BATCH_SIZE` | `10` | Number of messages to read per batch |
| `REDIS_CONSUMER_TIMEOUT` | `1000` | Timeout in milliseconds for reading messages |

### Service URLs

| Variable | Default | Description |
|----------|---------|-------------|
| `INTEGRATION_SERVICE_URL` | `http://localhost:8000/integration` | Integration service endpoint |
| `TMU_SERVICE_URL` | `http://localhost:8000/tmu` | Trade Management Unit endpoint |
| `SCANNING_SERVICE_URL` | `http://localhost:8000/scanning_service` | Scanning service endpoint |

### Service Communication Timeouts

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `SERVICE_CONNECT_TIMEOUT` | `10` | HTTP connection timeout in seconds |

### Django Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_DEBUG` | `True` | Enable Django debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hosts for Django |
| `DJANGO_SETTINGS_MODULE` | `ats_base.settings` | Django settings module |

## Queue Architecture

The system uses two main Redis streams for inter-service communication:

### 1. Scanning Queue (`scanning_queue`)
- **Producer**: Trade Management Unit (TMU)
- **Consumer**: Scanning Service
- **Purpose**: Initiates scanning when trade sessions are created
- **Event Types**: `trade_session_initiated`, `trade_session_terminated`

### 2. Initiation Queue (`initiation_queue`)
- **Producer**: Scanning Service
- **Consumer**: Initiation Service (to be implemented)
- **Purpose**: Carries eligible instruments found by scanners
- **Event Types**: `eligible_instrument_found`

**Standardized Event Format:**
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
  "market_price": 2475.30
}
```

**Field Requirements:**
- **Required**: `instrument_id`, `trading_symbol`, `market_price`
- **Optional**: `support_price`, `resistance_price`, `required_action` (null if not applicable)

### 3. Scanner Status Stream (`scanner_status_stream`)
- **Producer**: Scanning Service
- **Consumer**: Monitoring/Dashboard services
- **Purpose**: Real-time scanner status and metrics
- **Event Types**: `scanner_status_update`

## Docker Compose Configuration

All services in Docker Compose are configured with consistent environment variables:

```yaml
services:
  ats-app:
    environment:
      # Database Configuration
      - DATABASE_ENGINE=django.db.backends.mysql
      - DATABASE_NAME=ats_db
      - DATABASE_USER=ats_user
      - DATABASE_PASSWORD=ats_password
      - DATABASE_HOST=ats-db
      - DATABASE_PORT=3306
      
      # Redis Configuration
      - REDIS_HOST=ats-redis
      - REDIS_PORT=6379
      - REDIS_DB=0
      
      # Stream Configuration
      - REDIS_STREAM_SCANNING_QUEUE=scanning_queue
      - REDIS_STREAM_INITIATION_QUEUE=initiation_queue
      - REDIS_STREAM_SCANNER_STATUS=scanner_status_stream
      
      # Service URLs (for inter-container communication)
      - INTEGRATION_SERVICE_URL=http://ats-app:8000/integration
      - TMU_SERVICE_URL=http://ats-app:8000/tmu
      - SCANNING_SERVICE_URL=http://ats-app:8000/scanning_service
```

## Best Practices

### 1. Environment-First Configuration
- All configuration comes from environment variables
- Sensible defaults are provided for development
- Production values should be explicitly set

### 2. Service URLs
- Use container names in Docker Compose (`ats-app:8000`)
- Use proper service discovery in Kubernetes
- Use load balancers in production

### 3. Redis Configuration
- Adjust timeouts based on network latency
- Use Redis Cluster in production for high availability
- Monitor Redis memory usage and configure appropriate limits

### 4. Stream Naming
- Use descriptive stream names
- Follow consistent naming conventions
- Consider environment prefixes for multi-environment deployments

### 5. Timeouts
- Set appropriate timeouts for your network conditions
- Consider cascading timeout patterns (service timeout < load balancer timeout)
- Monitor timeout metrics and adjust accordingly

## Monitoring

### Key Metrics to Monitor

1. **Redis Metrics**:
   - Stream lengths
   - Consumer lag
   - Connection pool utilization
   - Memory usage

2. **Service Communication**:
   - Request/response times
   - Error rates
   - Timeout occurrences

3. **Scanner Performance**:
   - Scan cycle duration
   - Instruments processed per cycle
   - Eligible instruments found

### Health Checks

Each service provides health check endpoints:
- Redis connectivity
- Database connectivity
- Inter-service communication

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**:
   - Check `REDIS_HOST` and `REDIS_PORT` settings
   - Verify Redis container is running
   - Check network connectivity between containers

2. **Stream Processing Issues**:
   - Verify stream names match between producers and consumers
   - Check consumer group creation
   - Monitor message acknowledgment rates

3. **Service Communication Failures**:
   - Verify service URLs are correct for your environment
   - Check network policies and firewall rules
   - Monitor service health and availability

### Debug Commands

```bash
# Check Redis streams
docker exec -it ats-redis-server redis-cli
XINFO STREAM scanning_queue
XINFO STREAM initiation_queue

# Check service connectivity
docker exec -it ats-app curl http://ats-app:8000/health

# View logs
docker-compose logs -f ats-app | grep -i redis
docker-compose logs -f ats-scanning-service
```

## Migration Notes

### Changes in This Update

1. **Stream Renaming**: `eligible_instruments_stream` → `initiation_queue`
2. **Consistent Configuration**: All services now use the same environment variables
3. **Settings-Based Configuration**: Stream names and Redis settings come from Django settings
4. **Enhanced Docker Compose**: All required environment variables are now explicit
5. **Timeout Configuration**: Added configurable timeouts for better reliability

### Breaking Changes

- Stream name change requires updating any external consumers
- New environment variables need to be set in production deployments
- Redis client configuration changes may affect connection pooling 