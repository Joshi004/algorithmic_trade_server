import datetime as real_dt
import pytest
import calendar

from ats_gateway.utils import jwt_utils


class _FakeDatetimeModule:
    class datetime:
        @staticmethod
        def utcnow():
            # Use real current time by default so generated tokens are not expired
            return real_dt.datetime.utcnow()

    timedelta = real_dt.timedelta


def _approx_equal(a: int, b: int, tolerance_seconds: int = 1) -> bool:
    return abs(a - b) <= tolerance_seconds

def _exp_ts(value) -> int:
    """Normalize exp to epoch seconds for tolerant assertions."""
    if hasattr(value, 'timestamp'):
        return int(value.timestamp())
    return int(value)

def _to_epoch_seconds_utc(dt: real_dt.datetime) -> int:
    """Convert naive datetime assumed in UTC to epoch seconds without local tz skew."""
    if dt.tzinfo is None:
        return calendar.timegm(dt.timetuple())
    return int(dt.timestamp())


@pytest.mark.unit
class TestGenerateLLT:
    def test_generate_llt_has_expected_claims(self, monkeypatch):
        base_now = real_dt.datetime.utcnow()
        class _NowDatetime:
            class datetime:
                @staticmethod
                def utcnow():
                    return base_now
            timedelta = real_dt.timedelta
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _NowDatetime)
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'LLT_SECRET', raising=True)

        token = jwt_utils.generate_llt({'user_id': 'u1'})
        assert isinstance(token, str)

        payload = jwt_utils.decode_llt(token)
        assert payload is not None
        assert payload.get('user_id') == 'u1'
        assert payload.get('token_type') == 'llt'

        # exp is typically returned as a UNIX timestamp (int)
        expected_exp = _to_epoch_seconds_utc(base_now + real_dt.timedelta(hours=24))
        assert _approx_equal(_exp_ts(payload.get('exp')), expected_exp)

    def test_generate_token_delegates_to_llt(self, monkeypatch):
        base_now = real_dt.datetime.utcnow()
        class _NowDatetime:
            class datetime:
                @staticmethod
                def utcnow():
                    return base_now
            timedelta = real_dt.timedelta
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _NowDatetime)
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'LLT_SECRET', raising=True)

        token = jwt_utils.generate_token({'x': 1})
        payload = jwt_utils.decode_llt(token)
        assert payload is not None
        assert payload.get('token_type') == 'llt'
        assert payload.get('x') == 1


@pytest.mark.unit
class TestGenerateSLT:
    def test_generate_slt_has_expected_claims(self, monkeypatch):
        base_now = real_dt.datetime.utcnow()
        class _NowDatetime:
            class datetime:
                @staticmethod
                def utcnow():
                    return base_now
            timedelta = real_dt.timedelta
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _NowDatetime)
        monkeypatch.setattr(jwt_utils, 'SLT_SECRET_KEY', 'SLT_SECRET', raising=True)

        token = jwt_utils.generate_slt({'user_id': 'u1'})
        assert isinstance(token, str)

        payload = jwt_utils.decode_slt(token)
        assert payload is not None
        assert payload.get('user_id') == 'u1'
        assert payload.get('token_type') == 'slt'

        expected_exp = _to_epoch_seconds_utc(base_now + real_dt.timedelta(minutes=15))
        assert _approx_equal(_exp_ts(payload.get('exp')), expected_exp)


@pytest.mark.unit
class TestGenerateWebsocketToken:
    def test_generate_websocket_token_has_expected_claims(self, monkeypatch):
        base_now = real_dt.datetime.utcnow()
        class _NowDatetime:
            class datetime:
                @staticmethod
                def utcnow():
                    return base_now
            timedelta = real_dt.timedelta
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _NowDatetime)
        monkeypatch.setattr(jwt_utils, 'WEBSOCKET_SECRET_KEY', 'WS_SECRET', raising=True)

        token = jwt_utils.generate_websocket_token({'user_id': 'u1'})
        assert isinstance(token, str)

        payload = jwt_utils.decode_websocket_token(token)
        assert payload is not None
        assert payload.get('user_id') == 'u1'
        assert payload.get('token_type') == 'websocket'
        assert payload.get('scope') == 'websocket_only'

        expected_exp = _to_epoch_seconds_utc(base_now + real_dt.timedelta(seconds=30))
        assert _approx_equal(_exp_ts(payload.get('exp')), expected_exp)


@pytest.mark.unit
class TestDecodeIsolation:
    def test_decode_only_accepts_matching_types(self, monkeypatch):
        # Prepare deterministic time for all generations
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _FakeDatetimeModule)

        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'LLT_SECRET', raising=True)
        monkeypatch.setattr(jwt_utils, 'SLT_SECRET_KEY', 'SLT_SECRET', raising=True)
        monkeypatch.setattr(jwt_utils, 'WEBSOCKET_SECRET_KEY', 'WS_SECRET', raising=True)

        llt = jwt_utils.generate_llt({'k': 'v'})
        slt = jwt_utils.generate_slt({'k': 'v'})
        ws = jwt_utils.generate_websocket_token({'k': 'v'})

        assert jwt_utils.decode_llt(llt) is not None
        assert jwt_utils.decode_slt(llt) is None
        assert jwt_utils.decode_websocket_token(llt) is None

        assert jwt_utils.decode_slt(slt) is not None
        assert jwt_utils.decode_llt(slt) is None
        assert jwt_utils.decode_websocket_token(slt) is None

        assert jwt_utils.decode_websocket_token(ws) is not None
        assert jwt_utils.decode_llt(ws) is None
        assert jwt_utils.decode_slt(ws) is None


@pytest.mark.unit
class TestDecodeTokenFallback:
    def test_decode_token_returns_payload_for_llt_or_slt(self, monkeypatch):
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _FakeDatetimeModule)
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'LLT_SECRET', raising=True)
        monkeypatch.setattr(jwt_utils, 'SLT_SECRET_KEY', 'SLT_SECRET', raising=True)

        llt = jwt_utils.generate_llt({'a': 1})
        slt = jwt_utils.generate_slt({'b': 2})

        payload_llt = jwt_utils.decode_token(llt)
        payload_slt = jwt_utils.decode_token(slt)

        assert payload_llt is not None and payload_llt.get('a') == 1
        assert payload_slt is not None and payload_slt.get('b') == 2

    def test_decode_token_returns_none_for_malformed(self):
        assert jwt_utils.decode_token('not.a.jwt') is None


@pytest.mark.unit
class TestVerifyWrappers:
    def test_verify_helpers(self, monkeypatch):
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _FakeDatetimeModule)
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'LLT_SECRET', raising=True)
        monkeypatch.setattr(jwt_utils, 'SLT_SECRET_KEY', 'SLT_SECRET', raising=True)
        monkeypatch.setattr(jwt_utils, 'WEBSOCKET_SECRET_KEY', 'WS_SECRET', raising=True)

        llt = jwt_utils.generate_llt({'x': 1})
        slt = jwt_utils.generate_slt({'x': 1})
        ws = jwt_utils.generate_websocket_token({'x': 1})

        assert jwt_utils.verify_llt(llt) is True
        assert jwt_utils.verify_slt(slt) is True
        assert jwt_utils.verify_websocket_token(ws) is True
        assert jwt_utils.verify_token(llt) is True
        assert jwt_utils.verify_token(slt) is True

        # Tamper with token to force verification failure
        tampered = 'x' + llt[1:]
        assert jwt_utils.verify_llt(tampered) is False
        assert jwt_utils.verify_token('not.a.jwt') is False


@pytest.mark.unit
class TestExpiryHandling:
    def test_llt_valid_when_exp_in_future(self, monkeypatch):
        # Choose a fixed time still far before real now to make exp far future
        class _FutureDatetime:
            class datetime:
                @staticmethod
                def utcnow():
                    # Near current epoch; exp will be sufficiently in the future
                    return real_dt.datetime.utcnow()

            timedelta = real_dt.timedelta

        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _FutureDatetime)
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'LLT_SECRET', raising=True)

        llt = jwt_utils.generate_llt({'z': 1})
        assert jwt_utils.decode_llt(llt) is not None

    def test_llt_expired_returns_none(self, monkeypatch):
        # Generate token with an exp far in the past relative to real now
        class _PastDatetime:
            class datetime:
                @staticmethod
                def utcnow():
                    return real_dt.datetime(2000, 1, 1, 0, 0, 0)

            timedelta = real_dt.timedelta

        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _PastDatetime)
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'LLT_SECRET', raising=True)

        expired = jwt_utils.generate_llt({'z': 1})
        # Decoding should fail due to expired exp
        assert jwt_utils.decode_llt(expired) is None

    def test_websocket_expired_returns_none(self, monkeypatch):
        class _PastDatetime:
            class datetime:
                @staticmethod
                def utcnow():
                    return real_dt.datetime(2000, 1, 1, 0, 0, 0)

            timedelta = real_dt.timedelta

        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _PastDatetime)
        monkeypatch.setattr(jwt_utils, 'WEBSOCKET_SECRET_KEY', 'WS_SECRET', raising=True)

        expired_ws = jwt_utils.generate_websocket_token({'k': 'v'})
        assert jwt_utils.decode_websocket_token(expired_ws) is None

    def test_slt_expired_returns_none(self, monkeypatch):
        class _PastDatetime:
            class datetime:
                @staticmethod
                def utcnow():
                    return real_dt.datetime(2000, 1, 1, 0, 0, 0)

            timedelta = real_dt.timedelta

        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _PastDatetime)
        monkeypatch.setattr(jwt_utils, 'SLT_SECRET_KEY', 'SLT_SECRET', raising=True)

        expired_slt = jwt_utils.generate_slt({'k': 'v'})
        assert jwt_utils.decode_slt(expired_slt) is None


@pytest.mark.unit
class TestSecretIsolation:
    def test_wrong_secret_fails_to_decode(self, monkeypatch):
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _FakeDatetimeModule)
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'A', raising=True)
        token = jwt_utils.generate_llt({'p': 1})

        # Change secret used for decode to simulate mismatch
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'B', raising=True)
        assert jwt_utils.decode_llt(token) is None

    def test_cross_type_rejection(self, monkeypatch):
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _FakeDatetimeModule)
        monkeypatch.setattr(jwt_utils, 'LLT_SECRET_KEY', 'LLT_SECRET', raising=True)
        monkeypatch.setattr(jwt_utils, 'SLT_SECRET_KEY', 'SLT_SECRET', raising=True)
        monkeypatch.setattr(jwt_utils, 'WEBSOCKET_SECRET_KEY', 'WS_SECRET', raising=True)

        llt = jwt_utils.generate_llt({'v': 1})
        slt = jwt_utils.generate_slt({'v': 1})
        ws = jwt_utils.generate_websocket_token({'v': 1})

        assert jwt_utils.decode_slt(llt) is None
        assert jwt_utils.decode_websocket_token(llt) is None
        assert jwt_utils.decode_llt(slt) is None
        assert jwt_utils.decode_websocket_token(slt) is None
        assert jwt_utils.decode_llt(ws) is None
        assert jwt_utils.decode_slt(ws) is None


@pytest.mark.unit
class TestErrorHandling:
    def test_malformed_tokens_return_none_or_false(self):
        bad = 'not.a.jwt'
        assert jwt_utils.decode_llt(bad) is None
        assert jwt_utils.decode_slt(bad) is None
        assert jwt_utils.decode_websocket_token(bad) is None
        assert jwt_utils.verify_token(bad) is False

    def test_defaults_work_without_env(self, monkeypatch):
        # Use module defaults as configured; ensure round‑trip works
        monkeypatch.setattr('ats_gateway.utils.jwt_utils.datetime', _FakeDatetimeModule)
        token = jwt_utils.generate_llt({'q': 1})
        assert isinstance(token, str)
        assert jwt_utils.verify_token(token) is True

