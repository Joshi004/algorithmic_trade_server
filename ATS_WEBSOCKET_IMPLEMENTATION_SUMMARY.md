# WebSocket ATS Gateway Implementation

This implementation provides a real-time WebSocket-based gateway service for the ATS (Algorithmic Trading System) application using Django Channels and Redis.

## 🏗️ Architecture Overview

- **Gateway Service**: Handles WebSocket connections and manages subscriptions
- **Redis**: Used for channel layer communication and subscription counting
- **JWT Authentication**: Secured WebSocket connections using existing JWT system
- **Group Management**: Efficient subscriber counting and group management

## 📁 Files Created

### Core Gateway Components
- `ats_gateway/consumers/ats_consumer.py` - Main WebSocket consumer (ATSConsumer)
- `ats_gateway/utils/group_utils.py` - Group naming and Redis subscription management
- `ats_base/asgi.py` - Updated routing to include ATS WebSocket endpoint

### Scanner Service Integration
- `scanning_service/utils/websocket_publisher.py` - Independent publisher utility (no coupling with gateway)
- `scanning_service/examples/websocket_integration_example.py` - Example scanner implementation

### Client-Side Example
- `examples/websocket_client_example.js` - JavaScript client (ATSWebSocketClient) for UI integration

## 🔄 Flow Description

### 1. Connection Flow
1. UI establishes WebSocket connection to `ws://localhost:8000/ws/ats/`
2. JWT authentication using SLT cookie from existing system
3. Connection accepted, user receives confirmation with channel name

### 2. Subscription Flow
1. UI sends `subscribe_scanner` action with `algorithm_id` and `frequency`
2. Gateway creates group name: `scanner_<algorithm>_<frequency>` (e.g., `scanner_2_5min`)
3. Channel added to group, Redis subscription count incremented
4. UI receives success response with group name for storage

### 3. Publishing Flow
1. Scanner service checks subscription count using `should_run_scanner()`
2. If subscribers exist, scanner publishes updates via `ScannerWebSocketPublisher`
3. Messages forwarded to all subscribers in the group
4. No unnecessary processing when no subscribers

### 4. Unsubscription Flow
1. UI sends `unsubscribe_scanner` action
2. Channel removed from group, Redis count decremented
3. Auto-cleanup when count reaches zero

## 🛠️ Key Features

### ✅ Authentication
- JWT-based authentication using existing SLT tokens
- Automatic disconnection for unauthorized users
- Seamless integration with current auth system

### ✅ Subscription Management
- Consistent group naming convention
- Redis-based subscriber counting
- Automatic cleanup of empty groups
- Per-connection subscription tracking

### ✅ Scalability
- Only run scanners when there are active subscribers
- Efficient Redis-based group management
- Support for multiple concurrent subscribers
- Minimal resource usage when idle

### ✅ Real-Time Communication
- Instant scanner updates to subscribers
- Status notifications (started, stopped, error)
- Structured message format for easy parsing

## 📋 WebSocket Message Format

### Client to Server
```json
{
  "action": "subscribe_scanner",
  "algorithm_id": "2",
  "frequency": "5min"
}
```

### Server to Client - Subscription Success
```json
{
  "type": "subscription_success",
  "action": "subscribe_scanner",
  "group_name": "scanner_2_5min",
  "algorithm_id": "2",
  "frequency": "5min",
  "message": "Successfully subscribed to scanner_2_5min"
}
```

### Server to Client - Scanner Update
```json
{
  "type": "scanner_update",
  "algorithm_id": "2",
  "frequency": "5min",
  "group_name": "scanner_2_5min",
  "data": {
    "timestamp": "2024-01-15T10:30:00",
    "instruments_scanned": 150,
    "matches_found": 3,
    "scan_duration_ms": 120
  }
}
```

## 🚀 Usage Examples

### Scanner Service Integration
```python
from scanning_service.utils.websocket_publisher import ScannerWebSocketPublisher

# Initialize publisher for algorithm 2, 5-minute frequency
publisher = ScannerWebSocketPublisher(algorithm_id="2", frequency="5min")

# Check if anyone is subscribed before processing
if publisher.has_subscribers():
    # Perform scan and publish results
    scan_data = perform_scan()
    publisher.publish_scan_result(scan_data)
```

### Frontend JavaScript Client
```javascript
const client = new ATSWebSocketClient();

client.connect();
client.on('connected', () => {
    client.subscribeScanner(2, '5min');
});

client.on('scanResult', (message) => {
    console.log('New scan results:', message.data);
});
```

## ⚙️ Configuration

### Redis Settings (already configured)
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}
```

### WebSocket Endpoint
- **URL**: `ws://localhost:8000/ws/ats/`
- **Authentication**: JWT via SLT cookie
- **Protocol**: WebSocket with JSON messages

## 🎯 Benefits

1. **Efficient Resource Usage**: Only run scanners when subscribers exist
2. **Real-Time Updates**: Instant communication to connected clients
3. **Scalable**: Supports multiple subscribers and scanner algorithms
4. **Secure**: JWT authentication integration
5. **Maintainable**: Clean separation of concerns with utility modules
6. **Convention-Driven**: Consistent group naming and message formats

## 🔧 Integration Points

- **Existing JWT System**: Reuses SLT tokens for authentication
- **Redis Configuration**: Uses existing Redis setup
- **Django Channels**: Leverages configured channel layer
- **Service Decoupling**: Each service handles its own publishing independently

## 🎯 Service Architecture Benefits

1. **Complete Decoupling**: No imports between services
2. **Independent Publishing**: Each service manages its own WebSocket publishing
3. **Shared Conventions**: Common group naming and Redis patterns
4. **Scalable**: Services can be deployed and scaled independently

This implementation provides a robust foundation for real-time ATS communications while maintaining the system's minimalist, convention-driven, and properly decoupled microservice architecture. 