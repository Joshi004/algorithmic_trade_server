### Comprehensive Business‑Logic Test Plan for group_utils (Integration‑First)

This plan lists the tests we should add to gain high confidence in the Redis-backed subscription tracking utilities in `ats_gateway/utils/group_utils.py`. We will use real Redis (as in existing tests) and focus on observable behavior: key values, TTLs, and side effects. The functions under test are:

- `get_group_name(algorithm_id, frequency)`
- `increment_group_subscription(group_name)`
- `decrement_group_subscription(group_name)`
- `get_group_subscription_count(group_name)`
- `cleanup_group_subscription(group_name)`


#### Scope & Principles
- [x] Use real Redis via Docker (same infra as other tests); do not mock Redis by default.
- [x] Keep tests isolated by generating unique `group_name` values per test (e.g., suffix with UUID).
- [x] Validate TTL and counts by reading actual Redis state.
- [x] Avoid asserting into the private implementation of the Redis client; assert observable key state and return values.
- [x] Keep tests deterministic; do not rely on wall-clock passage except for TTL bounds checks.

### Test Style Guidelines (Plain, Simple, Readable)
- Keep tests brain‑dead simple: clear Arrange → Act → Assert.
- Prefer one scenario per test with explicit inputs and expected outputs.
- Avoid control flow inside test bodies unless necessary for cleanup.
- Use descriptive test names that state the scenario and expected outcome.
- Favor readability over DRY; duplicate small setup if it avoids indirection.
- Use unique Redis keys per test to avoid cross‑test interference.

---

## 1) get_group_name – Naming Convention and Stability

Purpose: Ensure group names are generated consistently and without implicit mutation of inputs.

- [x] Case N1 – Standard inputs produce expected format
  - Input: `algorithm_id=2`, `frequency='10-minute'`
  - Expect: returns `scanner_2_10-minute`

- [x] Case N2 – Frequency passed through without normalization
  - Input: `algorithm_id=5`, `frequency='5Min'`
  - Expect: returns `scanner_5_5Min` (no case/format changes)

- [x] Case N3 – Non‑string algorithm_id handled via f-string conversion
  - Input: `algorithm_id=UUID(...)` or `None`, `frequency='daily'`
  - Expect: returns `scanner_<str(algorithm_id)>_daily` (no exceptions)

---

## 2) increment_group_subscription – Count Behavior and TTL Guarantees

Purpose: Verify increments create/update the `subs:<group_name>` key, return the new count, and enforce TTL of ~3600 seconds on each call.

- [x] Case I1 – First increment creates key with count=1 and TTL set
  - Pre: ensure key `subs:<group_name>` does not exist
  - Act: call `increment_group_subscription(group_name)`
  - Expect:
    - Return value is `1`
    - Redis key exists with value `'1'`
    - TTL is within expected bounds (e.g., 1 ≤ ttl ≤ 3600)

- [x] Case I2 – Consecutive increments increase count and refresh TTL
  - Pre: start from nonexistent key
  - Act: call increment twice
  - Expect:
    - First call returns `1`, second returns `2`
    - TTL after second call is (approximately) reset close to 3600

- [x] Case I3 – Isolation between different groups
  - Act: increment two distinct `group_name` values
  - Expect: each key is independent with count `1`; TTLs are set for both keys

---

## 3) decrement_group_subscription – Non‑Negative Counts and Safe Floor

Purpose: Validate that decrement reduces the count, never goes below zero, and normalizes negative intermediate states back to zero.

- [x] Case D1 – Decrement from 2 to 1
  - Pre: increment twice to reach count=2
  - Act: decrement once
  - Expect: return `1`; Redis value `'1'`

- [x] Case D2 – Decrement from 1 to 0
  - Pre: increment once to reach count=1
  - Act: decrement once
  - Expect: return `0`; Redis value `'0'`

- [x] Case D3 – Decrement from nonexistent key floors to 0
  - Pre: ensure key does not exist
  - Act: decrement once
  - Expect: return `0`; Redis value `'0'`

Notes:
- Redis `DECR` on a missing key yields `-1`. The function corrects this by setting the key to `0` and returning `0`. Test should assert final stored value is `'0'`.
- TTL is not explicitly set on decrement; behavior is only to correct counts. Follow‑up cleanup is performed by `cleanup_group_subscription`.

---

## 4) get_group_subscription_count – Accurate Reads and Missing Key Handling

Purpose: Ensure reading the subscription count returns the expected integer and defaults to 0 for missing keys.

- [x] Case C1 – Returns integer count for existing key
  - Pre: increment twice
  - Act: get count
  - Expect: `2`

- [x] Case C2 – Returns 0 for missing key
  - Pre: ensure key absent
  - Act: get count
  - Expect: `0`

---

## 5) cleanup_group_subscription – Key Removal Semantics

Purpose: Validate that cleanup removes the key only when count ≤ 0 and leaves positive counts untouched.

- [x] Case CL1 – Deletes key when count is 0
  - Pre: ensure key exists with value `'0'` (e.g., decrement from 1 → 0)
  - Act: call `cleanup_group_subscription(group_name)`
  - Expect: key no longer exists

- [x] Case CL2 – No deletion when count > 0
  - Pre: set count to `'2'` (e.g., increment twice)
  - Act: cleanup
  - Expect: key is still present with same value


---

## Test File Location, Naming & Structure

- Location: `tests/ats_gateway/`
- File name: `test_group_utils.py`
- Markers: use `@pytest.mark.integration` and `@pytest.mark.redis` for tests that touch real Redis.
- Structure: group by function behavior for clarity:
  - `TestGetGroupName`
  - `TestIncrementGroupSubscription`
  - `TestDecrementGroupSubscription`
  - `TestGetGroupSubscriptionCount`
  - `TestCleanupGroupSubscription`
  - `TestLogging` (optional)
  - `TestResilience` (optional)

### Fixtures & Setup
- Use the shared `redis_data_manager` from `tests/utils/redis_data_manager.py` to interact with Redis where convenient (e.g., cleanup, stream length, direct client access).
- Prefer explicit key deletion in `teardown`/`finally` blocks to ensure isolation; generate unique `group_name` values with `uuid.uuid4().hex`.
- Example unique group helper:
  ```python
  import uuid
  group_name = f"scanner_test_{uuid.uuid4().hex}"
  redis_key = f"subs:{group_name}"
  ```

### Example Assertions (TTL & Count)
```python
from ats_gateway.utils.group_utils import (
    get_group_name,
    increment_group_subscription,
    decrement_group_subscription,
    get_group_subscription_count,
    cleanup_group_subscription,
)

# TTL bounds example after increment
count = increment_group_subscription(group_name)
ttl = redis_data_manager.redis_client.ttl(f"subs:{group_name}")
assert count == 1
assert ttl == -2 or (1 <= ttl <= 3600)  # -2 if Redis is configured without expire support; else within 1h
```

---

## Running Tests (container mode)
- Start infra: `docker-compose up -d`
- Full suite with coverage gate: `./run_tests.sh -v`
- Full suite without coverage (faster dev loop): `./run_tests.sh -v -c`
- Single file: `docker exec -it ats-django-app bash -lc "cd /app && pytest -v tests/ats_gateway/test_group_utils.py"`

### Mocking Guidelines (when necessary)
- Do not mock: Redis server (for main behavior tests), key TTL, counters.
- Allowed to mock:
  - `redis_client` methods in this module to simulate connection errors for resilience tests.
  - Logging capture via `caplog` for non‑fragile assertions.

### Out of Scope
- Unit‑testing `redis` library internals.
- Performance/load characteristics; these are functional correctness tests only.
- Cross‑process contention; we validate observable single‑process semantics.

This plan targets full coverage of the subscription tracking utilities with simple, readable tests and clear invariants around counts and TTLs.

