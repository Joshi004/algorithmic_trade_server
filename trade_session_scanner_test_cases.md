# Trade Session Scanner Management - Test Cases

## Overview
This document contains comprehensive test cases for the distributed trade session scanning system. The system involves trade session creation, distributed scanner management with Redis locking, singleton scanner instances, and real-time WebSocket communication.

## System Components Under Test
- Trade session creation and management
- Scanning service event processing (`scanning_queue_consumer.py`)
- Distributed locking mechanism (`scanner_lock_manager.py`)
- Scanner singleton behavior (`UDTSScanner.py`)
- WebSocket communication (`ats_consumer.py`)
- Frontend real-time updates (`LiveTradeSession.jsx`)

## Test Environment Setup
- Local Docker containers for backend services
- Redis instance for distributed locking and streams
- Database for trade sessions and scanner instances
- Multiple container instances to test distributed behavior

---

## Category 1: Basic Trade Session and Scanner Creation

### TC001: Single Trade Session Creation
**Objective**: Verify basic trade session creation triggers scanner startup
**Preconditions**: 
- Clean database (no existing scanner instances)
- Redis is running and accessible
- Single scanning service container is running

**Steps**:
1. Create a new trade session with:
   - Algorithm: "UDTS" 
   - Frequency: "5-minute"
   - User ID: "test_user_1"
2. Verify event is published to Redis stream 'scanning_queue'
3. Wait 5 seconds for event processing
4. Check database for `ScannerInstance` entry with:
   - algorithm: UDTS algorithm ID
   - frequency: "5-minute"
   - is_active: True
5. Check Redis for scanner lock key: `scanner_lock:{algorithm_id}:5-minute`
6. Verify scanner thread is running by checking logs for "Started scanner thread"
7. Verify WebSocket group is created: `scanner_UDTS_5-minute`

**Expected Results**:
- Trade session created successfully
- Scanner instance record created in database
- Redis lock acquired
- Scanner thread started
- WebSocket group ready for subscriptions

### TC002: Multiple Trade Sessions Same Algorithm+Frequency
**Objective**: Verify multiple trade sessions with same algorithm+frequency share single scanner
**Preconditions**: 
- TC001 completed successfully
- Same scanning service container running

**Steps**:
1. Create second trade session with identical parameters:
   - Algorithm: "UDTS"
   - Frequency: "5-minute" 
   - User ID: "test_user_2"
2. Verify event is published to Redis stream
3. Wait 5 seconds for event processing
4. Check database - should still have only ONE `ScannerInstance` for UDTS+5-minute
5. Check Redis - should still have same lock with same container ID
6. Verify scanner thread count hasn't increased (same thread serving both sessions)
7. Check both users can subscribe to same WebSocket group

**Expected Results**:
- Second trade session created
- No new scanner instance created (reusing existing)
- Same Redis lock maintained
- Single scanner thread serves both sessions
- Both users receive same scanner updates

### TC003: Different Algorithm or Frequency Creates New Scanner
**Objective**: Verify different algorithm+frequency combinations create separate scanners
**Preconditions**: TC001 completed

**Steps**:
1. Create trade session with different frequency:
   - Algorithm: "UDTS"
   - Frequency: "10-minute"
   - User ID: "test_user_3"
2. Create trade session with different algorithm:
   - Algorithm: "OTHER_ALGO" 
   - Frequency: "5-minute"
   - User ID: "test_user_4"
3. Check database for separate `ScannerInstance` entries
4. Check Redis for separate lock keys:
   - `scanner_lock:{udts_id}:10-minute`
   - `scanner_lock:{other_id}:5-minute`
5. Verify separate scanner threads running
6. Verify separate WebSocket groups created

**Expected Results**:
- Three separate scanner instances in database
- Three separate Redis locks
- Three separate scanner threads
- Three separate WebSocket groups

---

## Category 2: Distributed Locking and Container Management

### TC004: Second Container Cannot Acquire Same Lock
**Objective**: Verify distributed locking prevents duplicate scanners across containers
**Preconditions**: 
- TC001 completed with Container A
- Start second scanning service container (Container B)

**Steps**:
1. Create trade session that should trigger same UDTS+5-minute scanner
2. Verify event reaches Container B
3. Check Container B logs for lock acquisition attempt
4. Verify Container B logs show "Could not acquire lock" message
5. Verify Container B does NOT create scanner instance
6. Verify database still has only one scanner instance
7. Verify Redis lock still owned by Container A

**Expected Results**:
- Container B processes event but cannot acquire lock
- No duplicate scanner instances created
- Original scanner continues running on Container A
- System logs show expected "lock not acquired" behavior

### TC005: Lock Renewal During Scanning
**Objective**: Verify scanner lock is renewed periodically during operation
**Preconditions**: TC001 completed, scanner actively running

**Steps**:
1. Monitor Redis lock TTL for `scanner_lock:{algorithm_id}:5-minute`
2. Record initial TTL value
3. Wait for scanner to process some instruments (check progress updates)
4. Check Redis lock TTL has been renewed (higher value than expected decay)
5. Check scanner logs for "Successfully renewed scanner lock" messages
6. Verify scanner continues running without interruption

**Expected Results**:
- Lock TTL gets renewed periodically
- Scanner logs show successful lock renewals
- Scanner continues processing without stopping

### TC006: Lock Expiry Handling
**Objective**: Verify scanner stops gracefully when lock expires
**Preconditions**: TC001 completed

**Steps**:
1. Manually delete the Redis lock: `DEL scanner_lock:{algorithm_id}:5-minute`
2. Wait for next scanner progress save (when it tries to renew lock)
3. Check scanner logs for lock renewal failure
4. Verify scanner stops gracefully with "Lock now owned by container" message
5. Verify scanner thread terminates
6. Check database - scanner instance should remain but scanner stops processing

**Expected Results**:
- Scanner detects lock loss
- Scanner stops gracefully without errors
- Scanner thread terminates cleanly
- Database state remains consistent

### TC007: Container Takeover Scenario
**Objective**: Verify smooth takeover when original container loses lock
**Preconditions**: TC001 with Container A, Container B running

**Steps**:
1. Forcefully stop Container A (docker stop)
2. Wait for lock to expire (default 15 minutes or manually delete)
3. Create new trade session with same UDTS+5-minute parameters
4. Verify Container B acquires the lock
5. Verify Container B starts new scanner instance
6. Check database for scanner instance activation
7. Verify WebSocket clients can connect to new scanner

**Expected Results**:
- Container B successfully takes over
- New scanner starts on Container B
- WebSocket communication continues
- No data loss or corruption

---

## Category 3: WebSocket Communication and Real-time Updates

### TC008: WebSocket Subscription and Updates
**Objective**: Verify real-time scanner updates via WebSocket
**Preconditions**: TC001 completed, scanner running

**Steps**:
1. Open frontend application to Live Trade Session page
2. Navigate to trade session from TC001
3. Verify WebSocket connection establishes with authentication
4. Verify subscription to scanner group: `scanner_UDTS_5-minute`
5. Check browser console for "subscription_success" message
6. Monitor for real-time scanner updates:
   - progress_update messages
   - instrument_eligible messages
   - cycle_completed messages
7. Verify frontend displays live scanning progress
8. Verify eligible instruments appear in real-time

**Expected Results**:
- WebSocket connection authenticated successfully
- Subscription to correct scanner group
- Real-time updates received and displayed
- Frontend shows live scanning progress

### TC009: Multiple WebSocket Clients Same Group
**Objective**: Verify multiple clients can receive same scanner updates
**Preconditions**: TC001 completed

**Steps**:
1. Open two browser tabs/windows with same trade session
2. Verify both establish WebSocket connections
3. Verify both subscribe to same scanner group
4. Check Redis for group subscription count = 2
5. Trigger scanner updates (wait for scanning activity)
6. Verify both clients receive identical updates simultaneously
7. Close one tab, verify other continues receiving updates
8. Check Redis subscription count decreases to 1

**Expected Results**:
- Both clients connect and subscribe successfully
- Both receive identical real-time updates
- Subscription counting works correctly
- Graceful handling of client disconnections

### TC010: WebSocket Authentication Failure
**Objective**: Verify WebSocket rejects unauthenticated connections
**Preconditions**: Clean browser state (no auth cookies)

**Steps**:
1. Clear all authentication cookies/tokens
2. Try to access Live Trade Session page
3. Verify WebSocket connection attempt
4. Check for authentication failure (close code 4001)
5. Verify no scanner subscription occurs
6. Verify frontend shows "disconnected" state

**Expected Results**:
- WebSocket rejects connection due to auth failure
- No scanner subscriptions created
- Frontend handles disconnected state gracefully

---

## Category 4: Scanner Behavior and Data Processing

### TC011: Scanner Instrument Processing
**Objective**: Verify scanner processes instruments and finds eligible ones
**Preconditions**: TC001 completed, market data available

**Steps**:
1. Monitor scanner logs for instrument processing
2. Verify scanner fetches instrument list from TMU service
3. Check logs for "Scanning {symbol} now" messages
4. Verify volume eligibility checks are performed
5. Verify trend analysis is conducted
6. Check for eligible instruments found ("found next eligible instrument")
7. Verify eligible instruments are published via event publisher
8. Check WebSocket updates contain eligible instrument details

**Expected Results**:
- Scanner processes instruments sequentially
- Eligibility checks are performed correctly
- Eligible instruments are identified and published
- Real-time updates sent via WebSocket

### TC012: Scanner State Management and Resume
**Objective**: Verify scanner can resume from saved state after restart
**Preconditions**: Scanner running and has processed some instruments

**Steps**:
1. Allow scanner to process 100+ instruments
2. Verify state is saved in Redis (check for scanner state keys)
3. Gracefully stop the scanner (docker restart)
4. Create new trade session with same parameters
5. Verify new scanner resumes from last saved position
6. Check logs for "Resuming scanning from index X" message
7. Verify no duplicate processing of already-scanned instruments

**Expected Results**:
- Scanner state is saved periodically
- Scanner resumes from correct position after restart
- No duplicate processing occurs
- Efficient resource utilization

### TC013: Scanner Cycle Completion and Restart
**Objective**: Verify scanner completes cycles and starts new ones
**Preconditions**: TC001 with fast scanning (small instrument set or test mode)

**Steps**:
1. Monitor scanner for complete cycle
2. Verify "Scan cycle X completed" message
3. Check WebSocket update for "cycle_completed" event
4. Verify scanner starts next cycle automatically
5. Check cycle counter increments
6. Verify 30-second delay between cycles
7. Monitor multiple cycles to ensure stability

**Expected Results**:
- Scanner completes cycles successfully
- Automatic restart with proper delay
- Cycle tracking works correctly
- System remains stable across multiple cycles

---

## Category 5: Error Handling and Edge Cases

### TC014: Database Connection Failure
**Objective**: Verify graceful handling of database connectivity issues
**Preconditions**: System running normally

**Steps**:
1. Stop database container while scanner is running
2. Create new trade session (should fail gracefully)
3. Verify scanning service logs appropriate database errors
4. Verify scanner continues with existing connections if possible
5. Restart database
6. Verify system recovers automatically
7. Create new trade session and verify it works

**Expected Results**:
- Graceful error handling for database issues
- Appropriate error logging
- System recovery after database restoration
- No data corruption

### TC015: Redis Connection Failure
**Objective**: Verify behavior when Redis becomes unavailable
**Preconditions**: System running with active scanners

**Steps**:
1. Stop Redis container
2. Wait for lock renewal attempts to fail
3. Verify scanners stop gracefully
4. Verify WebSocket connections are terminated
5. Try creating new trade sessions (should fail)
6. Restart Redis
7. Verify system can recover and restart scanners

**Expected Results**:
- Scanners detect Redis failure and stop gracefully
- WebSocket connections handle Redis failure
- System recovers after Redis restoration
- Proper error logging throughout

### TC016: Invalid Event Data Handling
**Objective**: Verify system handles malformed or invalid events
**Preconditions**: System running normally

**Steps**:
1. Manually publish invalid event to Redis stream:
   - Missing required fields
   - Invalid algorithm name
   - Invalid frequency
   - Malformed JSON
2. Verify scanning service processes events gracefully
3. Check logs for appropriate error messages
4. Verify system continues processing valid events
5. Verify no system crashes or data corruption

**Expected Results**:
- Invalid events are handled gracefully
- Appropriate error logging
- System stability maintained
- Valid events continue to process

### TC017: High Load Scenario
**Objective**: Verify system performance under high load
**Preconditions**: Multiple containers running

**Steps**:
1. Rapidly create 20+ trade sessions with different algorithm+frequency combinations
2. Monitor system resource usage
3. Verify all scanner instances start correctly
4. Check for any lock conflicts or race conditions
5. Monitor WebSocket connection handling
6. Verify all scanners process instruments correctly
7. Check for any memory leaks or performance degradation

**Expected Results**:
- System handles high load gracefully
- All scanner instances start and run correctly
- No lock conflicts or race conditions
- Stable performance under load

---

## Category 6: Integration and End-to-End Tests

### TC018: Complete User Journey
**Objective**: Verify complete user experience from session creation to live updates
**Preconditions**: Clean system state

**Steps**:
1. User creates trade session via frontend
2. Navigate to Live Trade Session page
3. Verify WebSocket connection and scanner subscription
4. Wait for scanner to find eligible instruments
5. Verify eligible instruments appear in real-time on frontend
6. Verify trade statistics update correctly
7. Verify scanner logs show detailed instrument analysis
8. Let scanner complete one full cycle
9. Verify cycle completion updates on frontend

**Expected Results**:
- Seamless user experience from creation to live updates
- All real-time features work correctly
- Data consistency between backend and frontend
- Professional user interface with live updates

### TC019: Multi-User Same Scanner Scenario
**Objective**: Verify multiple users sharing same scanner receive consistent updates
**Preconditions**: System running

**Steps**:
1. User A creates UDTS+5-minute trade session
2. User B creates UDTS+5-minute trade session
3. Both users navigate to their respective Live Trade Session pages
4. Verify both connect to same WebSocket group
5. Wait for scanner to find eligible instruments
6. Verify both users see identical eligible instruments simultaneously
7. Verify both users see same progress updates
8. Have User A close their session
9. Verify User B continues receiving updates
10. Verify scanner continues running (singleton behavior)

**Expected Results**:
- Both users receive identical real-time updates
- Scanner singleton behavior works correctly
- Session closure doesn't affect other users
- Consistent data across all connected users

### TC020: Container Failure Recovery
**Objective**: Verify system recovers from container failures
**Preconditions**: Multiple users with active sessions

**Steps**:
1. Have active scanners running with users connected
2. Forcefully stop the container running the scanners
3. Wait for lock expiration or manually trigger
4. Verify backup container takes over scanner responsibilities
5. Verify WebSocket clients reconnect automatically
6. Verify users continue receiving scanner updates with minimal interruption
7. Verify data consistency maintained throughout

**Expected Results**:
- Seamless container failover
- Minimal service interruption
- WebSocket clients recover automatically
- Data consistency maintained
- Professional high-availability behavior

---

## Test Execution Guidelines

### Prerequisites for Testing
1. Docker environment with ability to run multiple containers
2. Access to Redis CLI for manual operations
3. Browser developer tools for WebSocket monitoring
4. Database admin tools for verification
5. Log monitoring capabilities

### Test Data Requirements
- Test user accounts with valid authentication
- Sample financial instrument data
- Market data for scanner processing
- Valid algorithm configurations

### Success Criteria
- All test cases pass without system crashes
- Appropriate error handling and logging
- Data consistency maintained across all scenarios
- Performance remains acceptable under load
- User experience remains professional and responsive

### Monitoring During Tests
- Container logs for all services
- Redis key states and TTL values
- Database record states
- WebSocket connection states
- Frontend console outputs
- System resource usage

## Notes for Local Testing
- Use Docker Compose to manage multiple container instances
- Set shorter lock TTL values for faster testing (modify `DEFAULT_SCANNER_LOCK_TTL_SECONDS`)
- Use smaller instrument datasets for faster test cycles
- Monitor Docker container resource usage
- Use Redis CLI to inspect keys and streams during testing
- Use browser network tools to monitor WebSocket traffic 