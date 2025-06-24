# Real-Time Scanner WebSocket Implementation Plan

## Executive Summary

This document outlines the implementation plan for adding real-time WebSocket connections to provide live scanner updates to the UI. The goal is to replace current HTTP polling mechanisms with efficient WebSocket connections that deliver real-time information about scanner progress, eligible instruments found, and session statistics.

## Current Architecture Analysis

### Existing Components
- **UDTSScanner**: Singleton scanner instances per frequency that find eligible instruments
- **ScanningEventPublisher**: Publishes eligible instruments to Redis streams
- **Trade Session HTTP APIs**: Provide session information via REST endpoints
- **JWT Authentication**: Uses HTTP-only cookies (SLT/LLT) for authentication
- **Multi-Session Scanner Relationship**: One scanner can serve multiple trade sessions

### Current Data Flow
```
UDTSScanner → ScanningEventPublisher → Redis Stream → Initiation Service
                                                    ↓
HTTP Polling ← UI ← Trade Session APIs ← Database
```

### Issues with Current Approach
1. **HTTP Polling Overhead**: Constant polling creates unnecessary server load
2. **Delayed Updates**: Polling intervals cause delays in real-time information
3. **Inefficient Resource Usage**: Multiple HTTP requests for minimal data changes
4. **Poor User Experience**: Delayed feedback on scanner progress and findings

## Proposed WebSocket Architecture

### High-Level Design
```
UDTSScanner → WebSocket Event Router → WebSocket Manager → UI Client
     ↓                                        ↑
Redis Stream → WebSocket Event Consumer → Connection Pool
```

### Key Design Decisions

#### 1. Connection Strategy: Per-User-Per-Session
- **One WebSocket connection per user per session**
- Connections established only when user navigates to session detail page
- Automatic connection cleanup when user leaves page
- Supports multiple concurrent connections for users with multiple sessions

#### 2. Authentication Strategy
- **Token-based WebSocket authentication** using existing JWT tokens
- Extract SLT token from HTTP-only cookie during WebSocket handshake
- Validate token using existing JWT middleware logic
- Maintain session-user mapping for message routing

#### 3. Event Routing Strategy
- **Scanner-to-Multiple-Sessions Publishing**: Maintain current publisher pattern
- **WebSocket Event Router**: New component to route scanner events to appropriate WebSocket connections
- **Connection Registry**: Track active WebSocket connections by user and session

## Technical Implementation Plan

### Phase 1: WebSocket Infrastructure Setup

#### 1.1 WebSocket Server Setup
```python
# Location: scanning_service/websocket/
# Files to create:
# - websocket_server.py
# - websocket_manager.py
# - connection_registry.py
# - websocket_auth.py
```

**Components:**
- **WebSocket Server**: Django Channels or standalone WebSocket server
- **Connection Manager**: Handle connection lifecycle
- **Authentication Handler**: Validate JWT tokens from cookies
- **Message Router**: Route events to appropriate connections

#### 1.2 WebSocket Authentication Module
```python
class WebSocketAuthenticator:
    def authenticate_websocket(self, headers, query_params):
        # Extract SLT token from cookie header
        # Validate using existing JWT utilities
        # Return user_id and validation result
```

**Key Features:**
- Parse HTTP-only cookies from WebSocket headers
- Reuse existing JWT validation logic (`decode_slt`)
- Handle token expiration gracefully
- Support automatic reconnection on token refresh

#### 1.3 Connection Registry
```python
class WebSocketConnectionRegistry:
    def register_connection(self, user_id, session_id, websocket):
        # Store connection mapping
    
    def get_connections_for_session(self, session_id):
        # Return all WebSocket connections for a session
    
    def remove_connection(self, user_id, session_id):
        # Cleanup connection
```

### Phase 2: Event Router Implementation

#### 2.1 WebSocket Event Router
```python
class WebSocketEventRouter:
    def route_scanner_event(self, event_data):
        # Route eligible instrument events to relevant connections
        # Handle scanner status updates
        # Manage session statistics updates
```

**Integration Points:**
- Hook into existing `ScanningEventPublisher`
- Subscribe to Redis streams for scanner events
- Route events based on `trade_session_id`

#### 2.2 Real-Time Event Types
```typescript
interface ScannerWebSocketEvents {
  // Scanner status updates
  scanner_status: {
    session_id: string;
    status: 'started' | 'running' | 'stopped' | 'error';
    progress: {
      current_index: number;
      total_instruments: number;
      scan_cycle: number;
      eligible_found: number;
      scan_duration?: number;
    }
  };
  
  // New eligible instrument found
  eligible_instrument: {
    session_id: string;
    instrument: {
      trading_symbol: string;
      market_price: number;
      support_price?: number;
      resistance_price?: number;
      required_action?: 'buy' | 'sell';
    };
    timestamp: string;
  };
  
  // Session statistics update
  session_stats: {
    session_id: string;
    stats: {
      total_trades: number;
      active_trades: number;
      total_profit: number;
      success_rate: number;
      last_activity: string;
    }
  };
  
  // Connection status
  connection_status: {
    status: 'connected' | 'disconnected' | 'reconnecting';
    message?: string;
  };
}
```

### Phase 3: Scanner Integration

#### 3.1 Modify UDTSScanner
```python
# In UDTSScanner.scan_in_separate_thread()
# Add WebSocket event publishing alongside Redis publishing

def _publish_scanner_progress(self, current_index, total_instruments, eligible_found):
    """Publish scanner progress to WebSocket connections"""
    websocket_router.route_scanner_progress({
        'scanner_type': 'udts',
        'frequency': self.frequency,
        'progress': {
            'current_index': current_index,
            'total_instruments': total_instruments,
            'eligible_found': eligible_found,
            'scan_cycle': self.scan_cycle
        }
    })
```

#### 3.2 Real-Time State Updates
- **Scanner Progress**: Update every N instruments scanned
- **Eligible Instruments**: Immediate notification when found
- **Scan Cycle Completion**: Summary statistics per cycle
- **Error Handling**: Connection failures and recovery

### Phase 4: Frontend Integration

#### 4.1 WebSocket Client Service
```typescript
class ScannerWebSocketService {
  private connections: Map<string, WebSocket> = new Map();
  
  connectToSession(sessionId: string): Promise<WebSocket> {
    // Establish WebSocket connection for specific session
    // Handle authentication via cookie
    // Setup event listeners
  }
  
  disconnectFromSession(sessionId: string): void {
    // Cleanup WebSocket connection
  }
  
  onScannerUpdate(callback: (event: ScannerWebSocketEvents) => void): void {
    // Register event callback
  }
}
```

#### 4.2 UI Integration Points
- **Session Detail Page**: Auto-connect when page loads
- **Scanner Status Component**: Real-time progress updates
- **Eligible Instruments List**: Live instrument additions
- **Session Statistics**: Real-time trade metrics
- **Connection Status Indicator**: Show WebSocket connection health

### Phase 5: Production Considerations

#### 5.1 Scalability
- **Connection Pooling**: Efficient memory usage for connections
- **Load Balancing**: Distribute WebSocket connections across servers
- **Redis Pub/Sub**: Scale event routing using Redis
- **Connection Limits**: Implement per-user connection limits

#### 5.2 Reliability
- **Heartbeat Mechanism**: Keep connections alive
- **Automatic Reconnection**: Handle network interruptions
- **Message Queuing**: Buffer messages during disconnections
- **Graceful Degradation**: Fallback to HTTP polling if WebSocket fails

#### 5.3 Security
- **Rate Limiting**: Prevent WebSocket abuse
- **Origin Validation**: Ensure connections from authorized domains
- **Token Validation**: Regular JWT token validation
- **Connection Monitoring**: Log and monitor WebSocket activity

## Implementation Timeline

### Week 1-2: Infrastructure Setup
- [ ] WebSocket server setup (Django Channels)
- [ ] Authentication module implementation
- [ ] Connection registry implementation
- [ ] Basic WebSocket routing

### Week 3-4: Event Router Development
- [ ] WebSocket event router implementation
- [ ] Redis stream integration
- [ ] Event type definitions
- [ ] Testing event routing

### Week 5-6: Scanner Integration
- [ ] Modify UDTSScanner for WebSocket events
- [ ] Implement real-time progress updates
- [ ] Add eligible instrument notifications
- [ ] Handle scanner lifecycle events

### Week 7-8: Frontend Development
- [ ] WebSocket client service
- [ ] UI component updates
- [ ] Real-time data binding
- [ ] Connection status handling

### Week 9-10: Testing & Optimization
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Load testing
- [ ] Security validation

### Week 11-12: Production Deployment
- [ ] Production configuration
- [ ] Monitoring setup
- [ ] Documentation
- [ ] Gradual rollout

## Message Format Specifications

### WebSocket Message Structure
```json
{
  "type": "scanner_status" | "eligible_instrument" | "session_stats" | "connection_status",
  "session_id": "string",
  "timestamp": "ISO 8601 string",
  "data": {
    // Type-specific data
  }
}
```

### Scanner Status Message
```json
{
  "type": "scanner_status",
  "session_id": "session_123",
  "timestamp": "2024-01-15T10:30:45+05:30",
  "data": {
    "status": "running",
    "scanner_type": "udts",
    "frequency": "5-minute",
    "progress": {
      "current_index": 150,
      "total_instruments": 500,
      "scan_cycle": 2,
      "eligible_found": 8,
      "scan_duration_seconds": 45.2
    }
  }
}
```

### Eligible Instrument Message
```json
{
  "type": "eligible_instrument",
  "session_id": "session_123",
  "timestamp": "2024-01-15T10:30:45+05:30",
  "data": {
    "instrument": {
      "trading_symbol": "RELIANCE",
      "instrument_id": "738561",
      "market_price": 2475.30,
      "support_price": 2450.50,
      "resistance_price": 2500.75,
      "required_action": "buy"
    },
    "sequence_number": 9
  }
}
```

## Authentication Flow

### WebSocket Connection Handshake
```
1. Client initiates WebSocket connection
2. Server extracts 'slt' cookie from headers
3. Server validates JWT token using existing middleware logic
4. If valid, connection established and registered
5. If invalid, connection rejected with 401 status
```

### Token Refresh Handling
```
1. Client detects SLT token expiration
2. Client refreshes token via existing HTTP endpoint
3. Client reconnects WebSocket with new token
4. Server validates new token and re-establishes connection
```

## Error Handling & Recovery

### Connection Failures
- **Network Issues**: Automatic reconnection with exponential backoff
- **Authentication Failures**: Clear error messages, redirect to login
- **Server Errors**: Graceful degradation to HTTP polling

### Message Delivery
- **Message Ordering**: Ensure proper event sequence
- **Duplicate Prevention**: Handle duplicate event scenarios
- **Buffer Management**: Handle high-frequency events efficiently

## Monitoring & Analytics

### WebSocket Metrics
- **Active Connections**: Number of active WebSocket connections
- **Message Throughput**: Messages per second by type
- **Connection Duration**: Average connection lifespan
- **Error Rates**: Authentication and connection failures

### Performance Metrics
- **Message Latency**: Time from scanner event to UI display
- **Resource Usage**: Memory and CPU usage for WebSocket server
- **Bandwidth Usage**: Data transfer optimization

## Security Considerations

### Authentication Security
- **Token Validation**: Regular JWT token validation
- **Session Binding**: Ensure users can only access their sessions
- **Rate Limiting**: Prevent abuse of WebSocket connections

### Data Security
- **Message Encryption**: Use WSS (WebSocket Secure) in production
- **Data Sanitization**: Validate all outgoing message data
- **Audit Logging**: Log WebSocket connection and activity

## Deployment Configuration

### Development Environment
```yaml
websocket:
  enabled: true
  host: "localhost"
  port: 8001
  max_connections: 100
  heartbeat_interval: 30
```

### Production Environment
```yaml
websocket:
  enabled: true
  host: "0.0.0.0"
  port: 8001
  max_connections: 1000
  heartbeat_interval: 30
  ssl_enabled: true
  rate_limit: 100  # messages per minute per connection
```

## Testing Strategy

### Unit Tests
- WebSocket authentication logic
- Connection registry operations
- Event routing functionality
- Message formatting

### Integration Tests
- End-to-end WebSocket communication
- Scanner event publishing
- JWT token validation
- Connection lifecycle management

### Load Tests
- Multiple concurrent connections
- High-frequency message publishing
- Memory usage under load
- Connection scaling limits

## Migration Strategy

### Gradual Rollout
1. **Phase 1**: Deploy WebSocket infrastructure (disabled)
2. **Phase 2**: Enable for internal testing users
3. **Phase 3**: Enable for limited user group (A/B testing)
4. **Phase 4**: Full rollout with HTTP polling fallback
5. **Phase 5**: Remove HTTP polling after stability confirmation

### Rollback Plan
- **Feature Flag**: Easy disable of WebSocket functionality
- **HTTP Fallback**: Maintain existing HTTP polling as backup
- **Monitoring**: Real-time monitoring for immediate rollback decision

## Success Metrics

### Performance Improvements
- **Latency Reduction**: Target 50% reduction in data update latency
- **Server Load**: Target 30% reduction in server requests
- **User Experience**: Improved real-time feedback and responsiveness

### Technical Metrics
- **Connection Stability**: >99% uptime for WebSocket connections
- **Message Delivery**: >99.9% successful message delivery rate
- **Resource Usage**: Minimal increase in server resource consumption

## Future Enhancements

### Phase 2 Features
- **Push Notifications**: Browser notifications for important events
- **Multiple Session Monitoring**: Dashboard view for multiple sessions
- **Historical Playback**: Replay scanner events for analysis
- **Advanced Filtering**: Client-side filtering of real-time events

### Scalability Improvements
- **Horizontal Scaling**: Multi-server WebSocket deployment
- **Event Streaming**: Apache Kafka integration for high-volume events
- **Caching Layer**: Redis caching for frequently accessed data
- **CDN Integration**: Edge-based WebSocket connections

This implementation plan provides a comprehensive approach to adding real-time WebSocket functionality while maintaining system reliability and security. The phased approach allows for careful testing and gradual rollout, ensuring minimal disruption to existing functionality. 