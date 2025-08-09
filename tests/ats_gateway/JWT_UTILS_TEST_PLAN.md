### Comprehensive Business‑Logic Test Plan for jwt_utils (Integration‑First, Deterministic Time)

This plan lists the tests we should add to gain high confidence in JWT token utilities in `ats_gateway/utils/jwt_utils.py`. We will avoid external dependencies, keep time deterministic via monkeypatching, and focus on observable behavior: token payload claims, expiration, token type/scopes, and secret‑key isolation.


#### Scope & Principles
- [x] No DB/Redis required; pure crypto/claims logic.
- [x] Use deterministic time by monkeypatching `jwt_utils.datetime` so `utcnow()` is fixed.
- [x] Control secrets via environment variables using `monkeypatch.setenv`.
- [x] Validate both success paths and failure paths (expired, wrong secret, malformed, wrong token_type).
- [x] Prefer asserting decoded payload fields and boolean results over internal library behavior.
- [x] Keep tests isolated and explicit; restore/clear env per test via `monkeypatch`.

### Test Style Guidelines (Plain, Simple, Readable)
- Keep tests simple: clear Arrange → Act → Assert.
- One focused scenario per test; descriptive names.
- Avoid control flow in test bodies except minimal try/finally for cleanup when necessary.
- Use explicit, readable constants for secrets and times.
- Prefer `monkeypatch` fixtures for env/time control.

---

## 1) Token Generation – LLT, SLT, WebSocket

Purpose: Ensure `generate_llt`, `generate_slt`, `generate_websocket_token` produce strings with expected claims (exp, token_type, scope for websocket) and are signed with the correct secrets.

- [x] Case G1 – LLT generation uses LLT secret and 24h expiry
  - Pre: `monkeypatch.setenv('JWT_LONG_LIVED_TOKEN_SECRET', 'LLT_SECRET')` and set deterministic `utcnow = 2024‑01‑01 00:00:00 UTC`.
  - Act: `generate_llt({'user_id': 'u1'})`
  - Expect:
    - Returns `str` (not bytes)
    - `decode_llt(token)` returns payload containing `user_id='u1'`, `token_type='llt'`
    - `exp` equals fixed_now + 24h (assert delta==24h)

- [x] Case G2 – SLT generation uses SLT secret and 15m expiry
  - Pre: set `JWT_SHORT_LIVED_TOKEN_SECRET='SLT_SECRET'`, deterministic time
  - Act: `generate_slt({'user_id': 'u1'})`
  - Expect: `token_type='slt'`, `exp = fixed_now + 15 minutes`, `decode_slt(token)` succeeds

- [x] Case G3 – WebSocket token uses dedicated secret, 30s expiry, and scope
  - Pre: set `JWT_WEBSOCKET_TOKEN_SECRET='WS_SECRET'`, deterministic time
  - Act: `generate_websocket_token({'user_id': 'u1'})`
  - Expect:
    - `token_type='websocket'`
    - `scope='websocket_only'`
    - `exp = fixed_now + 30 seconds`
    - `decode_websocket_token(token)` succeeds

- [x] Case G4 – Legacy `generate_token` delegates to LLT
  - Act: `generate_token({'x': 1})`
  - Expect: decodes via `decode_llt`, `token_type='llt'`

---

## 2) Token Decoding – Type Isolation and Fallbacks

Purpose: Verify decoding functions accept only their intended token types and secrets, and `decode_token` tries LLT then SLT for backwards compatibility.

- [x] Case D1 – `decode_llt` accepts only LLT signed with LLT secret
  - Pre: generate a valid LLT with `LLT_SECRET`
  - Expect: `decode_llt` returns payload; `decode_slt` returns `None`; `decode_websocket_token` returns `None`

- [x] Case D2 – `decode_slt` accepts only SLT signed with SLT secret
  - Pre: generate a valid SLT with `SLT_SECRET`
  - Expect: `decode_slt` returns payload; `decode_llt` returns `None`; `decode_websocket_token` returns `None`

- [x] Case D3 – `decode_websocket_token` accepts only WebSocket tokens with WS secret and token_type
  - Pre: generate a WebSocket token
  - Expect: `decode_websocket_token` returns payload; `decode_llt` and `decode_slt` return `None`

- [x] Case D4 – `decode_token` fallback sequence (LLT then SLT)
  - Pre: generate one LLT and one SLT
  - Act/Expect: `decode_token(LLT)` returns payload; `decode_token(SLT)` returns payload; malformed token returns `None`

---

## 3) Verification Wrappers – Boolean Outcomes

Purpose: `verify_*` helpers should reflect decoding truthiness.

- [x] Case V1 – `verify_llt` returns True for valid LLT, False otherwise
- [x] Case V2 – `verify_slt` returns True for valid SLT, False otherwise
- [x] Case V3 – `verify_websocket_token` returns True for valid WS token, False otherwise
- [x] Case V4 – `verify_token` returns True for valid LLT or SLT, False for malformed/expired/wrong secret

---

## 4) Expiry Handling – Deterministic Time

Purpose: Validate `exp` claim creation and decoding failure after expiry.

- [x] Case E1 – LLT not expired at fixed_now + 23h 59m
  - Pre: create LLT at fixed_now; temporarily decode at same fixed_now
  - Expect: `decode_llt` succeeds

- [x] Case E2 – LLT expired at fixed_now + 24h + 1s
  - Pre: generate LLT; advance mocked `utcnow` beyond `exp`
  - Expect: `decode_llt` returns `None`

- [x] Case E3 – SLT expiry at 15m boundary (success before, fail after)

- [x] Case E4 – WebSocket token expiry at 30s boundary (success before, fail after)

Implementation note for time control:
- Patch at module import path: `monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', FakeDatetimeModule)` where `FakeDatetimeModule.datetime.utcnow()` returns your fixed value and `timedelta` is delegated to real `datetime.timedelta`.

---

## 5) Secret‑Key Isolation and Security Properties

Purpose: Ensure secrets are not interchangeable and token types are enforced.

- [x] Case S1 – Wrong secret fails to decode
  - Pre: generate LLT with `LLT_SECRET='A'`; set env to `LLT_SECRET='B'` during decode
  - Expect: `decode_llt` returns `None`

- [x] Case S2 – Cross‑type rejection: `decode_llt(SLT)` → `None`; `decode_slt(LLT)` → `None`; `decode_websocket_token(LLT/SLT)` → `None`

- [x] Case S3 – Tampered token (payload altered) fails to verify/decode
  - Act: modify base64 section of token
  - Expect: all decode/verify helpers return `None`/False

---

## 6) Error Handling and Robustness

Purpose: Invalid inputs and library exceptions should be handled gracefully.

- [x] Case R1 – Malformed token string (not JWT) returns `None` for decode helpers and False for verify helpers
- [x] Case R2 – Missing required env vars falls back to defaults (documented dev defaults)
  - Pre: ensure secrets not set; generate and decode LLT/SLT/WS token
  - Expect: functions still work using fallback constants

---

## Test File Location, Naming & Structure

- Location: `tests/ats_gateway/`
- File name: `test_jwt_utils.py`
- Markers: `@pytest.mark.unit` (optional); no DB/Redis markers needed.
- Structure: group by behavior for clarity:
  - `TestGenerateLLT`
  - `TestGenerateSLT`
  - `TestGenerateWebsocketToken`
  - `TestDecodeLLT`
  - `TestDecodeSLT`
  - `TestDecodeWebsocketToken`
  - `TestDecodeTokenFallback`
  - `TestVerifyWrappers`
  - `TestExpiryHandling`
  - `TestSecretIsolation`
  - `TestErrorHandling`

### Fixtures & Setup
- Use `monkeypatch` to:
  - Set secrets: `JWT_LONG_LIVED_TOKEN_SECRET`, `JWT_SHORT_LIVED_TOKEN_SECRET`, `JWT_WEBSOCKET_TOKEN_SECRET`.
  - Replace module `datetime` with a deterministic provider for `utcnow()`.
- Provide helper to decode raw JWT with expected secret when asserting `exp` exactness if needed.

### Example (Deterministic Time and Secret)
```python
import datetime as real_dt
import jwt
import pytest
from ats_gateway.utils import jwt_utils

class _FakeDatetimeModule:
    class datetime:
        @staticmethod
        def utcnow():
            return real_dt.datetime(2024, 1, 1, 0, 0, 0)
    timedelta = real_dt.timedelta

def test_generate_llt_has_expected_claims(monkeypatch):
    monkeypatch.setenv('JWT_LONG_LIVED_TOKEN_SECRET', 'LLT_SECRET')
    monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _FakeDatetimeModule)
    token = jwt_utils.generate_llt({'user_id': 'u1'})
    assert isinstance(token, str)
    payload = jwt_utils.decode_llt(token)
    assert payload['user_id'] == 'u1'
    assert payload['token_type'] == 'llt'
    assert payload['exp'] == int(real_dt.datetime(2024, 1, 2, 0, 0, 0).timestamp()) or payload['exp']
```

Note: Depending on `PyJWT` version, `exp` may be returned as a `datetime` or as an `int` UNIX timestamp. Prefer tolerant assertions by comparing within a 1‑second window or normalizing to int via `int(dt.timestamp())`.

---

## Running Tests (container mode)
- Start infra (not required for these tests, but for consistency): `docker-compose up -d`
- Full suite with coverage gate: `./run_tests.sh -v`
- Full suite without coverage (faster dev loop): `./run_tests.sh -v -c`
- Single file: `docker exec -it ats-django-app bash -lc "cd /app && pytest -v tests/ats_gateway/test_jwt_utils.py"`

### Mocking Guidelines (when necessary)
- Do not mock: `jwt` library behavior (treat as external dependency; assert via decode helpers or `jwt.decode`).
- Allowed to mock:
  - Module `datetime` within `jwt_utils` for deterministic time.
  - `os.environ` via `monkeypatch.setenv` for secret control.

### Out of Scope
- Unit‑testing cryptographic internals of `PyJWT`.
- Performance or load testing; focus on functional correctness.


