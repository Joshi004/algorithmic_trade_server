### Comprehensive Business‑Logic Test Plan for ScanningQueueConsumer (Integration‑First)

This plan lists the tests we should add to gain high confidence in the consumer’s business logic. We will mock external dependencies (Redis clients, lock manager, scanner factory, DB lookups) and focus only on decision-making and control flow inside `ScanningQueueConsumer`.

#### Purpose
Define a precise, integration‑oriented test suite for `ScanningQueueConsumer` that validates its business logic (routing, decisions, locking, lifecycle, and cleanup) using real MySQL/Redis and minimal mocks. The goal is high confidence that the consumer behaves correctly under success and failure conditions without testing third‑party libraries.

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
  - [ ] Redis consumer created with intended group/name (confirm via behavior and exposed attributes; avoid fragile call asserts).
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
  - [ ] Initiated → `_handle_scanner_event(..., is_resume=False)` and returns its result.
  - [ ] Resumed → `_handle_scanner_event(..., is_resume=True)` and returns its result.
  - [ ] Terminated → returns True; does not call `_handle_scanner_event`.
  - [ ] Unknown type → returns True (skips safely).
  - [ ] Malformed payload/exception → returns False.

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

### Minimal Mocking Policy
- Do not mock: database access, Redis clients/streams, consumer group creation.
- Allowed to mock (to keep tests fast and deterministic):
  - Scanner instance methods to avoid threads: `fetch_instrument_tokens_and_start_tracking`, `is_running` (return lightweight values only).
  - `time.sleep` during retry paths (stub to no‑op).
  - Rarely, `ScannerAlgoFactory.get_scanner` to inject a lightweight fake scanner for configuration/start assertions.
- Prefer asserting observable state changes (DB rows, Redis locks/acks) over internal call counts.

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

