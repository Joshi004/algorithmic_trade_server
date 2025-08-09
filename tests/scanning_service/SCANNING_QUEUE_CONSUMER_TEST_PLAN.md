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
  - [x] Consumer reads the event and routes to resume handler.
  - [x] Lock key `scanner_lock:<algorithm_id>:<frequency>` is created in Redis and owned by this container (check via `ScannerLockManager.check_lock`).
  - [x] DB session remains `started` and `is_active=True` (no unintended DB changes from consumer itself).

#### 2.1.b) Resume event with no active sessions (safe no‑op)
- Steps:
  1) Ensure there are zero active `trade_sessions` for the given `(algorithm, frequency)`.
  2) Emit `resume_scanner` event (with or without IDs).
  3) Run consumer one iteration.
- Expected:
  - [x] Consumer routes to resume handler and returns False.
  - [x] No lock is created (or lock remains absent for that `(algorithm, frequency)`).
  - [x] Message is acknowledged or safely handled (configure expectation based on handler return and current logic; default: not acked when processing returns False).



---

## 3) Full Integration Test Suite – Event Types and Distributed Safety (Checklist)

This section defines the complete set of integration tests for `ScanningQueueConsumer` covering all three event types and distributed locking behavior. Each case uses real MySQL and Redis, an isolated Redis stream per test, and minimal stubs only at system boundaries (scanner start, external providers).

### 3.1 Start (trade_session_initiated) – New Session Path
- Purpose: When a Start event arrives, the consumer acquires the scanner lock for `(algorithm_id, frequency)`, orchestrates scanner startup, and acknowledges the event. Consumer does NOT create trade sessions (they are created by TMU).

- Preconditions (common):
  - [x] `scanning_algorithms` seeded (e.g., `UDTS`, id=1)
  - [x] Isolated Redis stream; consumer group created before publishing.
  - [x] (Optional) Pre-seed a `trade_sessions` row (status=`started`, is_active=1) to verify DB remains unchanged by consumer.

- Case A1 – Valid Start (no existing trade session row)
  - Steps:
    1) Do NOT pre-seed any `trade_sessions` row. Ensure `scanning_algorithms` is seeded (e.g., `UDTS`, id=1).
    2) Publish `trade_session_initiated` with valid `user_id`, `trade_session_id`, `trading_frequency`, `scanning_algorithm_name`, `initiation_algorithm_name`, `termination_algorithm_name`.
    3) Run the consumer for one bounded iteration.
   - Expected:
     - [x] Routed to `_handle_scanner_event(..., is_resume=False)` (assert `is_resume=False`).
     - [x] Redis Lock `scanner_lock:<algorithm_id>:<frequency>` is created and owned by this container.
     - [x] Scanner orchestration invoked (no-op scanner): `configure(...)` called with provided `user_id`, `trade_session_id`, `trading_frequency`.
     - [x] Event is acknowledged (no pending for the group/id).
     - [x] Database invariants: consumer does NOT create `trade_sessions`; verify table row count remains unchanged (still zero for this session id).

- Case A2 – Valid Start (existing trade session row)
  - Steps:
    1) Pre-seed a `trade_sessions` row with the same `trade_session_id` (status=`started`, `is_active=1`) created upstream by TMU.
    2) Publish `trade_session_initiated` with valid `user_id`, `trade_session_id`, `trading_frequency`, `scanning_algorithm_name`, `initiation_algorithm_name`, `termination_algorithm_name`.
    3) Run the consumer for one bounded iteration.
   - Expected:
     - [x] Routed to `_handle_scanner_event(..., is_resume=False)` (assert `is_resume=False`).
     - [x] Redis Lock `scanner_lock:<algorithm_id>:<frequency>` is created and owned by this container.
     - [x] Scanner orchestration invoked (no-op scanner): `configure(...)` called with provided `user_id`, `trade_session_id`, `trading_frequency`.
     - [x] Event is acknowledged (no pending for the group/id).
     - [x] Database invariants: pre-seeded `trade_sessions` row remains unchanged (same status, is_active, timestamps); no extra rows added.

- Case B – Invalid Start (bad algorithm)
  - Steps:
    1) Do NOT seed `scanning_algorithms` (or use a non-existent `scanning_algorithm_name`).
    2) Publish `trade_session_initiated` with otherwise valid fields.
   - Expected:
     - [x] Routed to start path (`is_resume=False`) but handler returns False due to missing algorithm.
     - [x] No Redis Lock is created.
    - [x] Event is not acknowledged (processing returned False).
     - [x] No DB changes.

### 3.2 Resume (resume_scanner)
- Purpose: On resume, the consumer should validate there are active sessions for `(algorithm_id, frequency)`; if yes, acquire lock and orchestrate; if not, perform a safe no‑op.
- Cases:
   - Case A – Valid Resume (active sessions exist)
     - [x] Routed with `is_resume=True`.
      - [x] Missing IDs in the event are filled from the first active session.
     - [x] Redis Lock created and owned.
      - [x] Event acknowledged.
     - [x] DB session remains `started` and `is_active=1` (no mutation by consumer).
   - Case B – Invalid Resume (no active sessions)
     - [x] Routed with `is_resume=True`.
     - [x] Returns False; no lock created.
     - [x] Event not acknowledged (processing returned False).
      - [x] No DB changes.
  - Case C – Invalid Resume (bad algorithm)
    - [x] Non-existent `scanning_algorithm_name`.
     - [x] Returns False; no lock; no ack; no DB changes.

### 3.3 Terminate (trade_session_terminated)
- Purpose: On terminate, the consumer acknowledges the event and logs; it does not stop scanners directly (scanners are frequency-based singletons managed separately) and does not release locks (unknown ownership across containers).
- Preconditions:
  - [x] Optional: pre-seed a session to represent the terminated one.
  - [x] Isolated stream; group created before publishing.
- Steps:
  1) Publish `trade_session_terminated` with relevant `trade_session_id`, `user_id` (optional).
  2) Run consumer one iteration.
- Expected (Checklist):
  - [x] Routed to termination handler; returns True.
  - [x] No attempt to acquire or release scanner locks.
  - [x] Event acknowledged.
  - [x] No DB changes by consumer.

### 3.4 Distributed Safety and Lock Ownership (Multi‑Consumer Cases)
- Purpose: Validate that locks prevent multiple containers from processing the same scanner concurrently and that events are safely handled when locks already exist.
- Cases:
  - Existing Lock Owned by Another Container on Resume/Start:
    - [x] Consumer detects existing lock for `(algorithm_id, frequency)`.
    - [x] Returns True with no further action (no scanner start in this consumer).
    - [x] Event acknowledged (or safely handled per current logic).
    - [x] Lock owner remains unchanged (still the other container).
  - Lock Owned by This Container (Re-entrant):
    - [x] Consumer recognizes ownership and may renew lock (heartbeat/TTL refresh where applicable).
    - [x] Event acknowledged; no duplicate scanner start.
  - Cross‑Stream Isolation:
    - [x] Events on test-specific stream are not consumed by background services (use isolated stream name and group).

### 3.5 Operational Resilience (within Start/Resume/Terminate where applicable)
- Include transient Redis behavior directly within the above scenarios:
  - [ ] ConnectionError/Timeout during read → logged and retried (sleep stubbed to no‑op); assert no crashes and eventual processing when message available.
   - [x] Unknown `event_type` → returns True (skip) without side effects.

---

## 4) Explicit Lock and State Artifacts to Verify (Reference)
 - Redis Locks:
   - [x] `scanner_lock:<algorithm_id>:<frequency>` created and owned by the processing container after successful Start/Resume.
   - [x] Not created on Resume when no active sessions.
    - [x] Not modified on Terminate.
  - Redis Acknowledgements:
    - [x] Success paths (Start, Resume with active) → message acked.
    - [ ] Failure path (Resume with no active, malformed event) → not acked.
 - Database (Consumer Invariants):
   - [x] Consumer does not create/update/delete rows in `trade_sessions` or algorithm tables; verify counts and specific row fields remain unchanged where pre-seeded.
   - [ ] Optional assertions on scanner heartbeat/status if later integrated via publisher utilities (out of current scope).
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

