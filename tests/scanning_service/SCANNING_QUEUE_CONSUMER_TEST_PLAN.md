### Comprehensive Business‑Logic Test Plan for ScanningQueueConsumer (Integration‑First)

This plan lists the tests we should add to gain high confidence in the consumer’s business logic. We will mock external dependencies (Redis clients, lock manager, scanner factory, DB lookups) and focus only on decision-making and control flow inside `ScanningQueueConsumer`.


#### Scope & Principles
- [x] Use real MySQL and Redis (via Docker) as in existing tests; do not mock DB/Redis.
- [x] Minimize mocking. Only mock parts that would spawn threads or external API work (e.g., scanner start) or add sleep delays.
- [x] Exercise business decisions and control flow; avoid asserting into library internals.
- [x] Bound the main loop predictably by shaping `read_from_stream` output and toggling `_running`.

### Test Style Guidelines (Plain, Simple, Readable)
- Keep tests brain‑dead simple: clear Arrange → Act → Assert; no cleverness.
- Avoid control flow inside tests (no loops/ifs/try/catch in test bodies unless absolutely necessary for cleanup).
- Prefer one focused scenario per test with explicit inputs and explicit expected outputs.
- Use descriptive test names that state the scenario and expected outcome.
- Favor readability over DRY: duplicate small setup if it avoids indirection.
- Use ASCII tables for DB setup to make data obvious at a glance.
- Minimize mocks; when needed, stub the smallest surface (e.g., scanner start, time.sleep).
- Keep assertions direct and high‑signal; avoid asserting implementation details of libraries.

## 1) Constructor initializes Redis consumer, lock manager, signal handlers, and default state
- Goal: Ensure the consumer starts in a safe, ready‑to‑run state with connections and handlers configured.
- Setup: Instantiate `ScanningQueueConsumer` with real Redis available.
- Steps: Inspect attributes and perform a `health_check()`.
- Expected:
  - [x] Attributes initialized (stream name, consumer group, consumer name prefix starting with `scanning_consumer_`).
  - [x] Redis consumer created with intended group/name (confirm via behavior and exposed attributes; avoid fragile call asserts).
  - [x] `ScannerLockManager` instance is present.
  - [x] SIGTERM/SIGINT handlers are registered.
  - [x] `_running` is False; `_scanner_factory` exists.
  - [x] `redis_consumer.health_check()` returns True.
  - [x] `stop_consuming()` keeps `_running` False.

## 2) _process_event correctly routes event types and handles bad payloads
- Goal: Validate that event routing calls the right handlers and that unknown/error cases are safe.
- Setup: Create a consumer; call `_process_event` with different payloads.
- Steps: Pass events for `trade_session_initiated`, `resume_scanner`, `trade_session_terminated`, unknown type, and malformed payload.
- Expected:
  - [x] Initiated → `_handle_scanner_event(..., is_resume=False)` and returns its result.
  - [x] Resumed → `_handle_scanner_event(..., is_resume=True)` and returns its result.
  - [ ] Terminated → returns True; does not call `_handle_scanner_event`.
  - [x] Unknown type → returns True (skips safely).
  - [x] Malformed payload/exception → returns False.

### 2.1) End‑to‑End Event Processing from Redis → Consumer → Effects (High‑Confidence Tests)
- Goal: Prove that real events placed on the Redis stream are consumed, routed, and produce the correct observable side‑effects (locks, acks, scanner orchestration), while keeping DB/Redis real and mocks minimal.
- Setup (common):
  - Seed DB with `users`, `scanning_algorithms`, `initiation_algorithms`, `termination_algorithms`, and `trade_sessions` as needed (ASCII tables below).
  - Clear stream `scanning_queue`.
  - Insert event into stream using `redis_data_manager.insert_stream_data(...)`.
  - Create `ScanningQueueConsumer`, set `_running=True`, and run `start_consuming()` for a bounded single pass (e.g., patch `time.sleep` to no‑op and set `_running=False` after first iteration).

#### 2.1.a) Resume event with active sessions (fills missing IDs)
- Steps:
  1) Seed one active `trade_sessions` row with status `started`, matching `scanning_algorithms.name='UDTS'` and `trading_frequency='10-minute'`.
  2) Emit `resume_scanner` event that omits `user_id` and/or `trade_session_id`.
  3) Run consumer one iteration.
- Expected:
  - [ ] Consumer reads the event and routes to resume handler.
  - [x] Lock key `scanner_lock:<algorithm_id>:<frequency>` is created in Redis and owned by this container (check via `ScannerLockManager.check_lock`).
  - [x] DB session remains `started` and `is_active=True` (no unintended DB changes from consumer itself).

#### 2.1.b) Resume event with no active sessions (safe no‑op)
- Steps:
  1) Ensure there are zero active `trade_sessions` for the given `(algorithm, frequency)`.
  2) Emit `resume_scanner` event (with or without IDs).
  3) Run consumer one iteration.
- Expected:
  - [ ] Consumer routes to resume handler and returns False.
  - [ ] No lock is created (or lock remains absent for that `(algorithm, frequency)`).
  - [ ] Message is acknowledged or safely handled (configure expectation based on handler return and current logic; default: not acked when processing returns False).
  - [ ] No DB changes occur.

#### 2.1.c) Initiated event (new session path)
- Steps:
  1) Seed `scanning_algorithms` with `UDTS` (id=1). A matching trade session may or may not exist; handler does not depend on session for start path.
  2) Emit `trade_session_initiated` event with valid fields (`user_id`, `trade_session_id`, `trading_frequency`).
  3) Run consumer one iteration.
- Expected:
  - [ ] Lock key for `(algorithm_id, frequency)` is created.
  - [ ] Scanner is orchestrated (minimally mock scanner start to avoid threads, but assert `configure(...)` arguments).
  - [ ] Message is acknowledged.
  - [ ] No unintended DB changes are made by the consumer.

#### 2.1.d) Terminated event (ack and skip scanner orchestration)
- Steps:
  1) Emit `trade_session_terminated` with fields for an existing session.
  2) Run consumer one iteration.
- Expected:
  - [ ] Consumer routes to termination handler and returns True.
  - [ ] No lock operations are performed.
  - [ ] Message is acknowledged.
  - [ ] DB remains unchanged by the consumer.

## 3) _handle_trade_session_terminated logs and returns success without side‑effects
- Goal: Confirm termination events are acknowledged without unintended actions.
- Expected:
  - [ ] Returns True and does not touch locks, factory, or scanners.

## 4) _handle_scanner_event handles database/locking edge cases deterministically
- Goal: Ensure robust behavior when inputs/state are missing or conflicting.
- Setup: Use real DB rows for `ScanningAlgorithm`/`TradeSession` where applicable (via ASCII tables). Keep Redis real; lock manager used as is.
- Expected per branch:
  - [ ] Algorithm not found (`DoesNotExist`) → returns False; no lock attempts.
  - [ ] Resume with zero active sessions → returns False; no lock attempts.
  - [ ] Resume with active sessions and existing lock → returns True without starting scanner.
  - [ ] Lock acquisition fails → returns True (someone else owns it).
  - [ ] Factory returns None → releases any held lock and returns False.
  - [ ] Scanner start raises → releases lock and returns False.

## 5) _handle_scanner_event starts scanners with correct configuration in success paths
- Goal: Validate happy paths for both new and resume flows.
- Setup: Seed DB with `ScanningAlgorithm` and, for resume, active `TradeSession` rows. Keep Redis real.
- Expected:
  - [ ] New session: acquires lock; builds providers; obtains scanner; calls `configure(...)` with provided user/session/frequency; invokes start; returns True.
  - [ ] Resume with missing IDs: fills `user_id`/`trade_session_id` from first active session; configures and starts; returns True.

Assertions for 4 & 5 (Business Outcomes):
- [ ] Locking outcomes are correct per branch (held/not held/released) and reflected in Redis lock keys.
- [ ] Factory is asked for the expected `(algorithm_name, frequency)`.
- [ ] Scanner receives correct config args; start is invoked exactly once on success.

## 6) start_consuming performs health checks and consumer‑group setup before looping
- Goal: Avoid entering the loop when prerequisites fail.
- Expected:
  - [ ] `health_check()` False → function returns early; `_running` remains False.
  - [ ] `ensure_consumer_group()` False → function returns early; no loop executed.

## 7) start_consuming processes messages and acks appropriately (success/failure paths)
- Goal: Validate message handling decisions and ack behavior.
- Setup: Feed `read_from_stream` one batch (then empty) using Redis. Toggle `_running` False after the first pass.
- Expected:
  - [ ] Success: `_process_event` True and `acknowledge_message` True → message is acked.
  - [ ] Ack failure: `_process_event` True but ack False → failure logged; continue.
  - [ ] Processing failure: `_process_event` False → not acked.
  - [ ] Exception while processing one message → caught/logged; other messages continue.

Technique: set `_running=True`, mock `read_from_stream` to return one batch then an empty list, and call `stop_consuming()` (or set `_running=False`) to exit.

## 8) start_consuming is resilient to Redis and generic exceptions inside the loop
- Goal: Ensure transient failures are handled without crashing the consumer.
- Expected:
  - [ ] On `redis.ConnectionError`, error is logged, `sleep` is invoked (mock to no‑op), then processing continues.
  - [ ] On `redis.TimeoutError`, timeout is logged and loop continues.
  - [ ] On generic Exception, error is logged and loop continues.

## 9) Cleanup closes Redis resources and resets state on any exit path
- Goal: Guarantee resource hygiene regardless of how the loop exits.
- Expected:
  - [ ] `finally` closes `redis_consumer` and `lock_manager.redis_client` when present.
  - [ ] `_running` is False after `start_consuming` returns.

## 10) stop_consuming flips the run flag and logs a clean stop
- Goal: Confirm the explicit stop pathway is safe and idempotent.
- Expected:
  - [x] Sets `_running=False` and logs stop without exceptions.

## 11) health_check accurately reflects underlying Redis health
- Goal: Provide a trustworthy readiness check.
- Expected:
  - [ ] Returns True/False exactly as `redis_consumer.health_check()` does.

---

### Test File Location, Naming & Structure
- Location: `tests/scanning_service/`
- File name: `test_scanning_queue_consumer.py` (group all consumer tests together to reuse fixtures and infra).
- Markers: put `@pytest.mark.integration`, `@pytest.mark.requires_db`, `@pytest.mark.redis` at class level for clarity and filtering.
- Structure: Group by behavior, e.g., `TestInitAndSetup`, `TestProcessEventRouting`, `TestHandleScannerEvent_Errors`, `TestHandleScannerEvent_Success`, `TestStartConsuming_Startup`, `TestStartConsuming_Messages`, `TestStartConsuming_Resilience`, `TestCleanup`, `TestStopConsuming`, `TestHealthCheck`.

### Fixtures & Data Setup (aligned with existing infra)
- Use real services via Docker (`docker-compose up -d`).
- Do not mock MySQL or Redis.
- Use `redis_data_manager` to clear streams and reset state between tests.
- Use `table_data_manager` to prepare DB rows with readable ASCII tables (e.g., `scanning_algorithms`, `trade_sessions`).
- Use `clean_db` when a fully clean DB is required before insertion.
- Settings: `tests.settings` is auto‑selected; `run_tests.sh` handles DB creation/migrations.

Example (ASCII table for `scanning_algorithms`):
```python
algos = """
+----+------+
| id | name |
+----+------+
| 1  | UDTS |
+----+------+
"""
table_data_manager.clear_table_completely('scanning_algorithms')
table_data_manager.insert_table_data('scanning_algorithms', algos)
```

Example (ASCII tables to seed a minimal Trade Session for resume tests):
```python
# 1) Users (must match ForeignKey in trade_sessions.user_id)
users = f"""
+----------------------+----------------------+
| public_id            | email                |
+----------------------+----------------------+
| {user_id}            | test@example.com     |
+----------------------+----------------------+
"""
table_data_manager.clear_table_completely('users')
table_data_manager.insert_table_data('users', users)

# 2) Algorithms (scanning/initiation/termination)
scanning_algos = """
+----+------+
| id | name |
+----+------+
| 1  | UDTS |
+----+------+
"""
init_algos = """
+----+------+
| id | name |
+----+------+
| 1  | Udts_slto |
+----+------+
"""
term_algos = init_algos
table_data_manager.clear_table_completely('scanning_algorithms')
table_data_manager.clear_table_completely('initiation_algorithms')
table_data_manager.clear_table_completely('termination_algorithms')
table_data_manager.insert_table_data('scanning_algorithms', scanning_algos)
table_data_manager.insert_table_data('initiation_algorithms', init_algos)
table_data_manager.insert_table_data('termination_algorithms', term_algos)

# 3) Trade session (status started, is_active=1)
trade_sessions = f"""
+----+--------------------------------------+---------------+----------------------+-------------------------+------------------+----------+-----------+------------------+-----------------------+------------------+
| id | user_id                              | status        | started_at           | closed_at               | dummy            | is_active| scanning_algorithm_id | initiation_algorithm_id | termination_algorithm_id | trading_frequency |
+----+--------------------------------------+---------------+----------------------+-------------------------+------------------+----------+-----------+------------------+-----------------------+------------------+
| 10 | {user_id}                            | started       | 2024-01-01 00:00:00  |                         | 0                | 1        | 1         | 1                | 1                     | 10-minute         |
+----+--------------------------------------+---------------+----------------------+-------------------------+------------------+----------+-----------+------------------+-----------------------+------------------+
"""
table_data_manager.clear_table_completely('trade_sessions')
table_data_manager.insert_table_data('trade_sessions', trade_sessions)
```

Example (Emit a real Redis resume event and run consumer one iteration):
```python
stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
redis_data_manager.clear_stream_completely(stream)
event = {
  'event_id': 'evt-1',
  'event_type': 'resume_scanner',
  'trade_session_id': '10',
  'user_id': str(user_id),
  'trading_frequency': '10-minute',
  'scanning_algorithm_name': 'UDTS',
  'initiation_algorithm_name': 'Udts_slto',
  'termination_algorithm_name': 'Udts_slto',
  'is_dummy': '0'
}
redis_data_manager.insert_stream_data(stream, event)

consumer = ScanningQueueConsumer()
consumer._running = True
# Let consumer read once then stop (e.g., patch time.sleep to set _running False) or call stop_consuming after asserting first pass.
consumer.start_consuming()

# Assert DB/Redis side-effects (e.g., lock key created, session remains started, acked entry count)
```

### Minimal Mocking Policy
- Do not mock: database access, Redis clients/streams, consumer group creation.
- Allowed to mock (to keep tests fast and deterministic):
  - Scanner instance methods to avoid threads: `fetch_instrument_tokens_and_start_tracking`, `is_running` (return lightweight values only).
  - `time.sleep` during retry paths (stub to no‑op).
  - Rarely, `ScannerAlgoFactory.get_scanner` to inject a lightweight fake scanner for configuration/start assertions.
- Prefer asserting observable state changes (DB rows, Redis locks/acks) over internal call counts.
 - For routing tests, keep minimal patching to target only the handler being routed to. For end‑to‑end consumer behavior tests, emit real Redis stream events and assert DB/lock outcomes without mocking handlers.

### Running Tests (container mode)
- Start infra: `docker-compose up -d`
- Full suite with coverage gate: `./run_tests.sh -v`
- Full suite without coverage (faster dev loop): `./run_tests.sh -v -c`
- Single file: `docker exec -it ats-django-app bash -lc "cd /app && pytest -v tests/scanning_service/test_scanning_queue_consumer.py"`

### Mocking Guidelines (when necessary)
- Patch at the consumer module import path, only when needed:
  - `scanning_service.consumers.scanning_queue_consumer.ScannerAlgoFactory`
  - `scanning_service.consumers.scanning_queue_consumer.time.sleep` (no‑op)
- Prefer asserting observable state and DB/Redis side‑effects over verifying calls into third‑party libraries.

### Out of Scope
- [x] Unit‑testing Redis/MySQL/Channels internals.
- [x] Scanner algorithm internals and external network calls.

This plan targets full branch coverage of the consumer’s business logic with clear, isolated tests.

