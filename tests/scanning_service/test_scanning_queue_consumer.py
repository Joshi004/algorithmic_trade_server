"""
Integration Tests for ScanningQueueConsumer

These tests verify the scanning queue consumer initialization and functionality
using real Redis integration and database connections. Tests cover consumer
initialization, signal handling, and Redis connection validation.
"""

import pytest
import signal
import time
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

from scanning_service.consumers.scanning_queue_consumer import ScanningQueueConsumer
from django.conf import settings
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.TradeSession import TradeSession
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm


@pytest.mark.integration
@pytest.mark.requires_db 
@pytest.mark.redis
class TestScanningQueueConsumerInitialization:
    """
    Integration Tests for ScanningQueueConsumer Initialization
    
    These tests verify the consumer initialization process including Redis client creation,
    lock manager initialization, signal handler setup, and initial state configuration.
    Tests use real Redis integration without mocking.
    """
    
    def test_successful_consumer_initialization(self, redis_data_manager):
        """
        Test Case A1.1: Successful Consumer Initialization
        
        Setup: Valid Redis configuration, accessible Redis server
        Action: Create ScanningQueueConsumer instance
        Verification:
            * Consumer name contains timestamp
            * Redis consumer client created successfully
            * Lock manager initialized
            * Signal handlers registered (SIGTERM, SIGINT)
            * _running flag set to False initially
        """
        # Clear any existing Redis state before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Store original signal handlers to restore later
        original_sigterm_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        try:
            # Record the time before creating consumer to verify timestamp in name
            time_before_creation = int(time.time())
            
            # Action: Create ScanningQueueConsumer instance
            consumer = ScanningQueueConsumer()
            
            # Record the time after creation
            time_after_creation = int(time.time())
            
            # Verification 1: Consumer name contains timestamp
            assert hasattr(consumer, 'consumer_name'), "Consumer should have consumer_name attribute"
            assert consumer.consumer_name.startswith('scanning_consumer_'), "Consumer name should start with 'scanning_consumer_'"
            
            # Extract timestamp from consumer name
            timestamp_part = consumer.consumer_name.replace('scanning_consumer_', '')
            consumer_timestamp = int(timestamp_part)
            
            # Verify timestamp is within expected range (allowing for processing time)
            assert time_before_creation <= consumer_timestamp <= time_after_creation, \
                f"Consumer timestamp {consumer_timestamp} should be between {time_before_creation} and {time_after_creation}"
            
            # Verification 2: Redis consumer client created successfully
            assert hasattr(consumer, 'redis_consumer'), "Consumer should have redis_consumer attribute"
            assert consumer.redis_consumer is not None, "Redis consumer client should be initialized"
            
            # Verify Redis client can perform basic operations
            assert consumer.redis_consumer.health_check() == True, "Redis consumer client should pass health check"
            
            # Verify stream name configuration
            expected_stream_name = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
            assert consumer.stream_name == expected_stream_name, f"Stream name should be {expected_stream_name}"
            
            # Verify consumer group configuration
            assert consumer.consumer_group == "scanning_service_group", "Consumer group should be 'scanning_service_group'"

            # Verify redis_consumer reflects the same group and generated name
            assert hasattr(consumer.redis_consumer, 'consumer_group'), "redis_consumer should expose consumer_group"
            assert hasattr(consumer.redis_consumer, 'consumer_name'), "redis_consumer should expose consumer_name"
            assert consumer.redis_consumer.consumer_group == consumer.consumer_group, "redis_consumer group should match consumer group"
            assert consumer.redis_consumer.consumer_name == consumer.consumer_name, "redis_consumer name should match generated consumer name"
            
            # Verification 3: Lock manager initialized
            assert hasattr(consumer, 'lock_manager'), "Consumer should have lock_manager attribute"
            assert consumer.lock_manager is not None, "Lock manager should be initialized"
            
            # Verify lock manager is properly configured
            from scanning_service.lib.utils.redis.scanner_lock_manager import ScannerLockManager
            assert isinstance(consumer.lock_manager, ScannerLockManager), "Lock manager should be ScannerLockManager instance"
            
            # Verification 4: Signal handlers registered (SIGTERM, SIGINT)
            # Check that signal handlers have been modified from default
            current_sigterm_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
            current_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
            
            # Restore handlers and check they were different from default
            signal.signal(signal.SIGTERM, current_sigterm_handler)
            signal.signal(signal.SIGINT, current_sigint_handler)
            
            assert current_sigterm_handler != signal.SIG_DFL, "SIGTERM handler should be customized"
            assert current_sigint_handler != signal.SIG_DFL, "SIGINT handler should be customized"
            
            # Verification 5: _running flag set to False initially
            assert hasattr(consumer, '_running'), "Consumer should have _running attribute"
            assert consumer._running == False, "Initial _running flag should be False"
            
            # Additional verification: Scanner factory initialized
            assert hasattr(consumer, '_scanner_factory'), "Consumer should have _scanner_factory attribute"
            assert consumer._scanner_factory is not None, "Scanner factory should be initialized"
            
            # Verify scanner factory type
            from scanning_service.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
            assert isinstance(consumer._scanner_factory, ScannerAlgoFactory), "Scanner factory should be ScannerAlgoFactory instance"
            
            # Verify consumer can be stopped gracefully
            consumer.stop_consuming()
            assert consumer._running == False, "_running should remain False after stop_consuming()"
            
        finally:
            # Cleanup: Restore original signal handlers
            signal.signal(signal.SIGTERM, original_sigterm_handler)
            signal.signal(signal.SIGINT, original_sigint_handler)
            
            # Cleanup Redis connections if consumer was created
            if 'consumer' in locals():
                try:
                    if hasattr(consumer, 'redis_consumer') and consumer.redis_consumer:
                        consumer.redis_consumer.close()
                except Exception as e:
                    # Ignore cleanup errors to avoid masking test failures
                    pass
                
                try:
                    if hasattr(consumer, 'lock_manager') and consumer.lock_manager:
                        if hasattr(consumer.lock_manager, 'redis_client') and consumer.lock_manager.redis_client:
                            consumer.lock_manager.redis_client.close()
                except Exception as e:
                    # Ignore cleanup errors to avoid masking test failures  
                    pass
            
            # Clear Redis state after test
            redis_data_manager.clear_stream_completely(scanning_queue) 


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestProcessEventRouting:
    """
    Routing tests for _process_event. These verify that:
    - Correct handler is called for each event type
    - Return values are propagated correctly
    - Unknown or malformed events are handled safely
    """

    def test_process_event_initiated_routes_and_returns_handler_result_without_mocks(self, table_data_manager):
        # Arrange: ensure algorithm is missing so handler will return False
        table_data_manager.clear_table_completely('scanning_algorithms')

        consumer = ScanningQueueConsumer()
        event = {
            'event_id': 'e1',
            'event_type': 'trade_session_initiated',
            'trade_session_id': 'ts1',
            # Let default scanning_algorithm_name = 'UDTS' which is not present
        }
        try:
            # Act
            result = consumer._process_event(event)

            # Assert: routed into handler and returned its (False) outcome
            assert result is False
        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass

    def test_process_event_resume_routes_and_returns_handler_result_without_mocks(self, table_data_manager):
        # Arrange: ensure algorithm is missing or no active sessions, handler returns False
        table_data_manager.clear_table_completely('scanning_algorithms')

        consumer = ScanningQueueConsumer()
        event = {
            'event_id': 'e2',
            'event_type': 'resume_scanner',
            'trade_session_id': 'ts2',
        }
        try:
            # Act
            result = consumer._process_event(event)

            # Assert: routed into resume handler and returned False (no alg/session)
            assert result is False
        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass

    def test_process_event_terminated_returns_true_no_handler_called(self):
        # Arrange
        consumer = ScanningQueueConsumer()
        event = {
            'event_id': 'e3',
            'event_type': 'trade_session_terminated',
            'trade_session_id': 'ts3'
        }
        try:
            # Act
            result = consumer._process_event(event)
            # Assert
            assert result is True
        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass

    def test_process_event_unknown_type_returns_true(self):
        # Arrange
        consumer = ScanningQueueConsumer()
        event = {
            'event_id': 'e4',
            'event_type': 'some_new_event',
            'trade_session_id': 'ts4'
        }
        try:
            # Act
            result = consumer._process_event(event)
            # Assert
            assert result is True
        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass

    def test_process_event_malformed_payload_returns_false(self):
        # Arrange
        consumer = ScanningQueueConsumer()
        bad_event = None  # Triggers AttributeError when calling .get
        try:
            # Act
            result = consumer._process_event(bad_event)
            # Assert
            assert result is False
        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestEndToEndResumeEvent:
    """
    End-to-end test for 2.1.a: Resume event with active sessions (fills missing IDs),
    using real DB and Redis, minimal mocks, and asserting observable effects.
    """

    def test_resume_with_active_session_creates_lock_and_acks_message(self, table_data_manager, redis_data_manager, test_user_id):
        # Arrange: use an isolated stream to avoid interference from background consumers
        test_stream = f"scanning_queue_test_{uuid.uuid4().hex[:8]}"
        setattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', test_stream)
        stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(stream)
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.clear_table_completely('scanning_algorithms')
        table_data_manager.clear_table_completely('initiation_algorithms')
        table_data_manager.clear_table_completely('termination_algorithms')
        table_data_manager.clear_table_completely('users')

        # Seed users (User.public_id FK in trade_sessions)
        # MySQL UUIDField stored as 32-char hex; include required user fields
        user_public_hex = test_user_id.hex
        users_ascii = f"""
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        | email                  | public_id                      | first_name| last_name | is_active | date_joined          | password                                 | is_staff   | is_superuser |
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        | test@example.com       | {user_public_hex}              | Test      | User      | 1         | 2024-01-01 00:00:00  | pbkdf2_sha256$test$hash                  | 0          | 0            |
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        """

        # Add is_superuser separately to satisfy strict MySQL without defaults
        # (include via direct SQL update after insert if needed)

        # Seed algorithms
        scanning_algos_ascii = """
        +----+------+-------------+-----------+----------------------+----------------------+
        | id | name | description | is_active | created_at           | updated_at           |
        +----+------+-------------+-----------+----------------------+----------------------+
        | 1  | UDTS | test algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------+-------------+-----------+----------------------+----------------------+
        """
        init_algos_ascii = """
        +----+------------+-------------+-----------+----------------------+----------------------+
        | id | name       | description | is_active | created_at           | updated_at           |
        +----+------------+-------------+-----------+----------------------+----------------------+
        | 1  | Udts_slto  | init algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------------+-------------+-----------+----------------------+----------------------+
        """
        term_algos_ascii = init_algos_ascii

        # Seed an active trade session
        trade_sessions_ascii = f"""
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        | id | user_id                        | status  | started_at           | dummy | is_active | scanning_algorithm_id  | initiation_algorithm_id  | termination_algorithm_id  | trading_frequency |
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        | 10 | {user_public_hex}              | started | 2024-01-01 00:00:00  | 0     | 1         | 1                      | 1                        | 1                         | 10-minute        |
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        """

        # Insert data
        table_data_manager.insert_table_data('users', users_ascii)
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algos_ascii)
        # Seed initiation and termination algorithms to satisfy FK constraints for trade_sessions (once)
        table_data_manager.clear_table_completely('initiation_algorithms')
        table_data_manager.clear_table_completely('termination_algorithms')
        init_algos_ascii_once = """
        +----+------------+-------------+-----------+----------------------+----------------------+
        | id | name       | description | is_active | created_at           | updated_at           |
        +----+------------+-------------+-----------+----------------------+----------------------+
        | 1  | Udts_slto  | init algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------------+-------------+-----------+----------------------+----------------------+
        """
        table_data_manager.insert_table_data('initiation_algorithms', init_algos_ascii_once)
        table_data_manager.insert_table_data('termination_algorithms', init_algos_ascii_once)
        table_data_manager.insert_table_data('trade_sessions', trade_sessions_ascii)

        consumer = ScanningQueueConsumer()
        # Ensure group exists BEFORE emitting the event so XREADGROUP('>') will see it
        assert consumer.redis_consumer.ensure_consumer_group(stream) is True

        # Ensure no stale lock exists from previous runs
        try:
            consumer.lock_manager.redis_client.delete("scanner_lock:1:10-minute")
        except Exception:
            pass

        # Emit resume event with missing IDs (consumer should fill from active session)
        event = {
            'event_id': 'evt-1',
            'event_type': 'resume_scanner',
            # intentionally omit user_id and use trade_session_id to still exercise fill path
            'trade_session_id': '10',
            'trading_frequency': '10-minute',
            'scanning_algorithm_name': 'UDTS',
            'initiation_algorithm_name': 'Udts_slto',
            'termination_algorithm_name': 'Udts_slto',
            'is_dummy': '0'
        }
        redis_data_manager.insert_stream_data(stream, event)

        # Minimal fake scanner to avoid real threads/APIs
        class _FakeScanner:
            def __init__(self):
                self._lock_manager = None
                self._algorithm_id = None
                self._frequency = None
                self._configured = False
            def configure(self, **kwargs):
                self._configured = True
            def fetch_instrument_tokens_and_start_tracking(self, user_id, trade_session_id, is_dummy):
                return None
            def is_running(self):
                return False

        class _FakeFactory:
            def get_scanner(self, name, freq):
                return _FakeScanner()

        # Act: run one bounded iteration (set running true then stop after first pass)
        try:
            consumer._running = True
            # Ensure group exists so read/ack works
            assert consumer.redis_consumer.ensure_consumer_group(stream) is True

            # Inject our lightweight factory and stub external providers
            consumer._scanner_factory = _FakeFactory()
            # Capture routing: wrap _handle_scanner_event to record is_resume flag
            routed = {'called': False, 'is_resume': None}
            _orig_handle = consumer._handle_scanner_event
            def _wrapped_handle(event_data, is_resume=False):
                routed['called'] = True
                routed['is_resume'] = is_resume
                return _orig_handle(event_data, is_resume=is_resume)
            consumer._handle_scanner_event = _wrapped_handle
            with patch('scanning_service.consumers.scanning_queue_consumer.IntegrationServiceProvider', return_value=object()), \
                 patch('scanning_service.consumers.scanning_queue_consumer.TMUServiceProvider', return_value=object()):
                # Trigger one read; after read, stop the loop by setting flag
                messages = consumer.redis_consumer.read_from_stream(stream, count=10, block=500)
                if messages:
                    for _stream, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            success = consumer._process_event(fields)
                            if success:
                                consumer.redis_consumer.acknowledge_message(stream, message_id)
            consumer._running = False

            # Assert: lock key exists/owned
            # Use the same lock manager instance as the consumer for consistency
            lock_mgr = consumer.lock_manager
            exists, owner = lock_mgr.check_lock(1, '10-minute')
            assert exists is True
            assert owner is not None and owner != ''

            # Assert: consumer routed to resume handler with is_resume=True
            assert routed['called'] is True
            assert routed['is_resume'] is True

            # Assert: session remains started and active
            ts = TradeSession.objects.get(id=10)
            assert ts.user_id.public_id.hex == user_public_hex
            assert ts.status == 'started'
            assert ts.is_active is True

            # Soft check: acknowledge of non-existent ID should be false, implying prior ack likely done
            assert consumer.redis_consumer.acknowledge_message(stream, '0-0') in (False, 0)

        finally:
            # Cleanup consumer resources
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestEndToEndResumeEventNoActive:
    """
    End-to-end test for 2.1.b: Resume event with no active sessions (safe no-op).
    Uses real DB/Redis, isolated stream, and minimal stubs for external providers.
    """

    def test_resume_with_no_active_session_does_not_create_lock(self, table_data_manager, redis_data_manager):
        # Arrange: isolated stream, no trade_sessions, but algorithm exists
        test_stream = f"scanning_queue_test_{uuid.uuid4().hex[:8]}"
        setattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', test_stream)
        stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(stream)

        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.clear_table_completely('scanning_algorithms')

        scanning_algos_ascii = """
        +----+------+-------------+-----------+----------------------+----------------------+
        | id | name | description | is_active | created_at           | updated_at           |
        +----+------+-------------+-----------+----------------------+----------------------+
        | 1  | UDTS | test algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------+-------------+-----------+----------------------+----------------------+
        """
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algos_ascii)

        consumer = ScanningQueueConsumer()
        assert consumer.redis_consumer.ensure_consumer_group(stream) is True

        # Ensure no stale lock exists
        try:
            consumer.lock_manager.redis_client.delete("scanner_lock:1:10-minute")
        except Exception:
            pass

        # Emit resume event (no active sessions exist for this algo/frequency)
        event = {
            'event_id': 'evt-no-active',
            'event_type': 'resume_scanner',
            'trading_frequency': '10-minute',
            'scanning_algorithm_name': 'UDTS',
            'initiation_algorithm_name': 'Udts_slto',
            'termination_algorithm_name': 'Udts_slto',
            'is_dummy': '0'
        }
        redis_data_manager.insert_stream_data(stream, event)

        # Minimal factory and provider stubs
        class _FakeScanner:
            def configure(self, **kwargs):
                return None
            def fetch_instrument_tokens_and_start_tracking(self, user_id, trade_session_id, is_dummy):
                return None
            def is_running(self):
                return False
        class _FakeFactory:
            def get_scanner(self, name, freq):
                return _FakeScanner()

        consumer._scanner_factory = _FakeFactory()

        # Track routing and ack behavior
        routed = {'called': False, 'is_resume': None}
        _orig_handle = consumer._handle_scanner_event
        def _wrapped_handle(event_data, is_resume=False):
            routed['called'] = True
            routed['is_resume'] = is_resume
            return _orig_handle(event_data, is_resume=is_resume)
        consumer._handle_scanner_event = _wrapped_handle

        acked = []

        try:
            messages = consumer.redis_consumer.read_from_stream(stream, count=10, block=500)
            if messages:
                for _stream, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        success = consumer._process_event(fields)
                        # Expect False -> do not acknowledge
                        if success:
                            consumer.redis_consumer.acknowledge_message(stream, message_id)
                            acked.append(message_id)

            # Assert: routed to resume and returned False (no active sessions)
            assert routed['called'] is True
            assert routed['is_resume'] is True

            # Assert: no lock created for (1, '10-minute')
            exists, owner = consumer.lock_manager.check_lock(1, '10-minute')
            assert exists is False

            # Assert: no ack attempted since success was False
            assert len(acked) == 0

            # Assert: DB unchanged (no sessions since we cleared table)
            assert TradeSession.objects.count() == 0

        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestEndToEndStartEventNoExistingSession:
    """
    3.1 Case A1 – Valid Start of trade session with no existing trade session row.
    Asserts routing (is_resume=False), Redis lock creation, scanner configure args,
    message acknowledgement, and that no trade_session row is created by the consumer.
    """

    def test_start_valid_no_existing_session_creates_lock_and_acks_without_creating_session(self, table_data_manager, redis_data_manager, test_user_id):
        # Arrange: isolated stream
        test_stream = f"scanning_queue_test_{uuid.uuid4().hex[:8]}"
        setattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', test_stream)
        stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(stream)

        # Seed required scanning algorithm
        table_data_manager.clear_table_completely('scanning_algorithms')
        scanning_algos_ascii = """
        +----+------+-------------+-----------+----------------------+----------------------+
        | id | name | description | is_active | created_at           | updated_at           |
        +----+------+-------------+-----------+----------------------+----------------------+
        | 1  | UDTS | test algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------+-------------+-----------+----------------------+----------------------+
        """
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algos_ascii)

        # Ensure no trade session row exists with this ID
        start_session_id = 42
        assert TradeSession.objects.filter(id=start_session_id).exists() is False

        consumer = ScanningQueueConsumer()
        assert consumer.redis_consumer.ensure_consumer_group(stream) is True

        # Clear any stale lock key
        try:
            consumer.lock_manager.redis_client.delete("scanner_lock:1:10-minute")
        except Exception:
            pass

        # Emit start event with valid fields
        event = {
            'event_id': 'evt-start-A1',
            'event_type': 'trade_session_initiated',
            'trade_session_id': str(start_session_id),
            'user_id': str(test_user_id),
            'trading_frequency': '10-minute',
            'scanning_algorithm_name': 'UDTS',
            'initiation_algorithm_name': 'Udts_slto',
            'termination_algorithm_name': 'Udts_slto',
            'is_dummy': '0'
        }
        redis_data_manager.insert_stream_data(stream, event)

        # No-op scanner capturing configure args
        class _CapturingScanner:
            def __init__(self):
                self.configure_called = False
                self.configure_kwargs = None
            def configure(self, **kwargs):
                self.configure_called = True
                self.configure_kwargs = kwargs
            def fetch_instrument_tokens_and_start_tracking(self, user_id, trade_session_id, is_dummy):
                return None
            def is_running(self):
                return False

        class _Factory:
            def __init__(self):
                self.last_scanner = None
            def get_scanner(self, name, freq):
                self.last_scanner = _CapturingScanner()
                return self.last_scanner

        factory = _Factory()
        consumer._scanner_factory = factory

        # Wrap handler to capture routing flag
        routed = {'called': False, 'is_resume': None}
        _orig_handle = consumer._handle_scanner_event
        def _wrapped_handle(event_data, is_resume=False):
            routed['called'] = True
            routed['is_resume'] = is_resume
            return _orig_handle(event_data, is_resume=is_resume)
        consumer._handle_scanner_event = _wrapped_handle

        # Act
        try:
            with patch('scanning_service.consumers.scanning_queue_consumer.IntegrationServiceProvider', return_value=object()), \
                 patch('scanning_service.consumers.scanning_queue_consumer.TMUServiceProvider', return_value=object()):
                acked = []
                messages = consumer.redis_consumer.read_from_stream(stream, count=10, block=500)
                if messages:
                    for _stream, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            success = consumer._process_event(fields)
                            if success:
                                consumer.redis_consumer.acknowledge_message(stream, message_id)
                                acked.append(message_id)

            # Assert routing to start path
            assert routed['called'] is True
            assert routed['is_resume'] is False

            # Assert lock acquired
            exists, owner = consumer.lock_manager.check_lock(1, '10-minute')
            assert exists is True
            assert owner is not None and owner != ''

            # Assert scanner configured with provided args
            assert factory.last_scanner is not None and factory.last_scanner.configure_called is True
            cfg = factory.last_scanner.configure_kwargs
            assert cfg is not None
            assert cfg.get('trade_freq') == '10-minute'
            assert cfg.get('user_id') == str(test_user_id)
            assert cfg.get('trade_session_id') == str(start_session_id)

            # Assert event was acknowledged (acked list has this id)
            assert len(acked) == 1

            # DB invariants: consumer did NOT create the trade session row
            assert TradeSession.objects.filter(id=start_session_id).exists() is False

        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestEndToEndStartEventWithExistingSession:
    """
    3.1 Case A2 – Valid Start of trade session with an existing trade session row.
    Asserts routing (is_resume=False), Redis lock creation, scanner configure args,
    message acknowledgement, and that the pre-seeded trade_session row remains unchanged.
    """

    def test_start_valid_existing_session_lock_ack_db_unchanged(self, table_data_manager, redis_data_manager, test_user_id):
        # Arrange: isolated stream
        test_stream = f"scanning_queue_test_{uuid.uuid4().hex[:8]}"
        setattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', test_stream)
        stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(stream)

        # Seed users (needed for trade_sessions FK)
        user_public_hex = test_user_id.hex
        table_data_manager.clear_table_completely('users')
        users_ascii = f"""
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        | email                  | public_id                      | first_name| last_name | is_active | date_joined          | password                                 | is_staff   | is_superuser |
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        | test_existing@example.com | {user_public_hex}          | Test      | User      | 1         | 2024-01-01 00:00:00  | pbkdf2_sha256$test$hash                  | 0          | 0            |
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        """
        table_data_manager.insert_table_data('users', users_ascii)

        # Seed required algorithms (scanning/initiation/termination)
        table_data_manager.clear_table_completely('scanning_algorithms')
        table_data_manager.clear_table_completely('initiation_algorithms')
        table_data_manager.clear_table_completely('termination_algorithms')
        scanning_algos_ascii = """
        +----+------+-------------+-----------+----------------------+----------------------+
        | id | name | description | is_active | created_at           | updated_at           |
        +----+------+-------------+-----------+----------------------+----------------------+
        | 1  | UDTS | test algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------+-------------+-----------+----------------------+----------------------+
        """
        init_algos_ascii = """
        +----+------------+-------------+-----------+----------------------+----------------------+
        | id | name       | description | is_active | created_at           | updated_at           |
        +----+------------+-------------+-----------+----------------------+----------------------+
        | 1  | Udts_slto  | init algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------------+-------------+-----------+----------------------+----------------------+
        """
        term_algos_ascii = init_algos_ascii
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algos_ascii)
        table_data_manager.insert_table_data('initiation_algorithms', init_algos_ascii)
        table_data_manager.insert_table_data('termination_algorithms', term_algos_ascii)

        # Seed existing trade session row
        table_data_manager.clear_table_completely('trade_sessions')
        start_session_id = 77
        trade_sessions_ascii = f"""
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        | id | user_id                        | status  | started_at           | dummy | is_active | scanning_algorithm_id  | initiation_algorithm_id  | termination_algorithm_id  | trading_frequency |
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        | {start_session_id} | {user_public_hex}      | started | 2024-01-01 00:00:00  | 0     | 1         | 1                      | 1                        | 1                         | 10-minute        |
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        """
        table_data_manager.insert_table_data('trade_sessions', trade_sessions_ascii)

        # Consumer setup
        consumer = ScanningQueueConsumer()
        assert consumer.redis_consumer.ensure_consumer_group(stream) is True
        try:
            consumer.lock_manager.redis_client.delete("scanner_lock:1:10-minute")
        except Exception:
            pass

        # Publish start event
        event = {
            'event_id': 'evt-start-A2',
            'event_type': 'trade_session_initiated',
            'trade_session_id': str(start_session_id),
            'user_id': str(test_user_id),
            'trading_frequency': '10-minute',
            'scanning_algorithm_name': 'UDTS',
            'initiation_algorithm_name': 'Udts_slto',
            'termination_algorithm_name': 'Udts_slto',
            'is_dummy': '0'
        }
        redis_data_manager.insert_stream_data(stream, event)

        # No-op scanner factory
        class _Scanner:
            def __init__(self):
                self.configure_called = False
                self.configure_kwargs = None
            def configure(self, **kwargs):
                self.configure_called = True
                self.configure_kwargs = kwargs
            def fetch_instrument_tokens_and_start_tracking(self, user_id, trade_session_id, is_dummy):
                return None
            def is_running(self):
                return False
        class _Factory:
            def __init__(self):
                self.last_scanner = None
            def get_scanner(self, name, freq):
                self.last_scanner = _Scanner()
                return self.last_scanner
        factory = _Factory()
        consumer._scanner_factory = factory

        # Capture routing
        routed = {'called': False, 'is_resume': None}
        _orig = consumer._handle_scanner_event
        def _wrap(ev, is_resume=False):
            routed['called'] = True
            routed['is_resume'] = is_resume
            return _orig(ev, is_resume=is_resume)
        consumer._handle_scanner_event = _wrap

        # Act
        try:
            with patch('scanning_service.consumers.scanning_queue_consumer.IntegrationServiceProvider', return_value=object()), \
                 patch('scanning_service.consumers.scanning_queue_consumer.TMUServiceProvider', return_value=object()):
                acked = []
                messages = consumer.redis_consumer.read_from_stream(stream, count=10, block=500)
                if messages:
                    for _s, msgs in messages:
                        for message_id, fields in msgs:
                            if consumer._process_event(fields):
                                consumer.redis_consumer.acknowledge_message(stream, message_id)
                                acked.append(message_id)

            # Assert routing and lock
            assert routed['called'] is True
            assert routed['is_resume'] is False
            exists, owner = consumer.lock_manager.check_lock(1, '10-minute')
            assert exists is True and owner

            # Assert scanner configured with provided args
            assert factory.last_scanner is not None and factory.last_scanner.configure_called is True
            cfg = factory.last_scanner.configure_kwargs
            assert cfg is not None
            assert cfg.get('trade_freq') == '10-minute'
            assert cfg.get('user_id') == str(test_user_id)
            assert cfg.get('trade_session_id') == str(start_session_id)

            # Assert event acked
            assert len(acked) == 1

            # Assert DB invariants: pre-seeded row remains unchanged
            ts = TradeSession.objects.get(id=start_session_id)
            assert ts.user_id.public_id.hex == user_public_hex
            assert ts.status == 'started'
            assert ts.is_active is True

        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestEndToEndStartEventInvalidAlgorithm:
    """
    3.1 Case B – Invalid Start (bad algorithm): no algorithm seeded or non-existent algorithm name.
    Expect: routed to start path, returns False, no lock, no ack, no DB changes.
    """

    def test_start_invalid_algorithm_no_lock_no_ack_no_db_changes(self, table_data_manager, redis_data_manager, test_user_id):
        # Arrange
        test_stream = f"scanning_queue_test_{uuid.uuid4().hex[:8]}"
        setattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', test_stream)
        stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(stream)

        table_data_manager.clear_table_completely('scanning_algorithms')
        table_data_manager.clear_table_completely('trade_sessions')

        consumer = ScanningQueueConsumer()
        assert consumer.redis_consumer.ensure_consumer_group(stream) is True
        try:
            consumer.lock_manager.redis_client.delete("scanner_lock:1:10-minute")
        except Exception:
            pass

        start_session_id = 99
        event = {
            'event_id': 'evt-start-B',
            'event_type': 'trade_session_initiated',
            'trade_session_id': str(start_session_id),
            'user_id': str(test_user_id),
            'trading_frequency': '10-minute',
            'scanning_algorithm_name': 'UDTS',  # not seeded
            'initiation_algorithm_name': 'Udts_slto',
            'termination_algorithm_name': 'Udts_slto',
            'is_dummy': '0'
        }
        redis_data_manager.insert_stream_data(stream, event)

        # Capture routing and ack attempts
        routed = {'called': False, 'is_resume': None}
        _orig = consumer._handle_scanner_event
        def _wrap(ev, is_resume=False):
            routed['called'] = True
            routed['is_resume'] = is_resume
            return _orig(ev, is_resume=is_resume)
        consumer._handle_scanner_event = _wrap
        acked = []

        # Act
        try:
            messages = consumer.redis_consumer.read_from_stream(stream, count=10, block=500)
            if messages:
                for _s, msgs in messages:
                    for message_id, fields in msgs:
                        success = consumer._process_event(fields)
                        if success:
                            consumer.redis_consumer.acknowledge_message(stream, message_id)
                            acked.append(message_id)

            # Assert: routed to start path, returned False
            assert routed['called'] is True
            assert routed['is_resume'] is False

            # No lock created
            exists, owner = consumer.lock_manager.check_lock(1, '10-minute')
            assert exists is False

            # No ack happened
            assert len(acked) == 0

            # No DB changes for the session
            assert TradeSession.objects.filter(id=start_session_id).exists() is False

        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestEndToEndResumeEventMissingIDs:
    """
    3.2 Case A – Valid Resume with active sessions and missing IDs filled from first active session.
    Asserts: routed is_resume=True, IDs filled, lock created, event acked, DB unchanged (still started & active).
    """

    def test_resume_missing_ids_filled_and_ack(self, table_data_manager, redis_data_manager, test_user_id):
        # Arrange: isolated stream and seed active session
        test_stream = f"scanning_queue_test_{uuid.uuid4().hex[:8]}"
        setattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', test_stream)
        stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(stream)

        # Seed user and algorithms
        user_hex = test_user_id.hex
        table_data_manager.clear_table_completely('users')
        users_ascii = f"""
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        | email                  | public_id                      | first_name| last_name | is_active | date_joined          | password                                 | is_staff   | is_superuser |
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        | test_resume@example.com| {user_hex}                     | Test      | User      | 1         | 2024-01-01 00:00:00  | pbkdf2_sha256$test$hash                  | 0          | 0            |
        +------------------------+--------------------------------+-----------+-----------+-----------+----------------------+------------------------------------------+------------+--------------+
        """
        table_data_manager.insert_table_data('users', users_ascii)

        table_data_manager.clear_table_completely('scanning_algorithms')
        scanning_algos_ascii = """
        +----+------+-------------+-----------+----------------------+----------------------+
        | id | name | description | is_active | created_at           | updated_at           |
        +----+------+-------------+-----------+----------------------+----------------------+
        | 1  | UDTS | test algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------+-------------+-----------+----------------------+----------------------+
        """
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algos_ascii)

        # Seed active trade session for (algo=1, freq=10-minute)
        # Also seed initiation/termination algorithms to satisfy FK constraints
        table_data_manager.clear_table_completely('initiation_algorithms')
        table_data_manager.clear_table_completely('termination_algorithms')
        init_algos_ascii = """
        +----+------------+-------------+-----------+----------------------+----------------------+
        | id | name       | description | is_active | created_at           | updated_at           |
        +----+------------+-------------+-----------+----------------------+----------------------+
        | 1  | Udts_slto  | init algo   | 1         | 2024-01-01 00:00:00  | 2024-01-01 00:00:00  |
        +----+------------+-------------+-----------+----------------------+----------------------+
        """
        term_algos_ascii = init_algos_ascii
        table_data_manager.insert_table_data('initiation_algorithms', init_algos_ascii)
        table_data_manager.insert_table_data('termination_algorithms', term_algos_ascii)

        table_data_manager.clear_table_completely('trade_sessions')
        trade_sessions_ascii = f"""
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        | id | user_id                        | status  | started_at           | dummy | is_active | scanning_algorithm_id  | initiation_algorithm_id  | termination_algorithm_id  | trading_frequency |
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        | 10 | {user_hex}                     | started | 2024-01-01 00:00:00  | 0     | 1         | 1                      | 1                        | 1                         | 10-minute        |
        +----+--------------------------------+---------+----------------------+-------+-----------+------------------------+--------------------------+---------------------------+------------------+
        """
        table_data_manager.insert_table_data('trade_sessions', trade_sessions_ascii)

        consumer = ScanningQueueConsumer()
        assert consumer.redis_consumer.ensure_consumer_group(stream) is True
        try:
            consumer.lock_manager.redis_client.delete("scanner_lock:1:10-minute")
        except Exception:
            pass

        # Emit resume event with missing IDs (omit both user_id and trade_session_id)
        event = {
            'event_id': 'evt-resume-missing',
            'event_type': 'resume_scanner',
            'trading_frequency': '10-minute',
            'scanning_algorithm_name': 'UDTS',
            'initiation_algorithm_name': 'Udts_slto',
            'termination_algorithm_name': 'Udts_slto',
            'is_dummy': '0'
        }
        redis_data_manager.insert_stream_data(stream, event)

        # Capturing scanner
        class _CapScanner:
            def __init__(self):
                self.configure_called = False
                self.configure_kwargs = None
            def configure(self, **kwargs):
                self.configure_called = True
                self.configure_kwargs = kwargs
            def fetch_instrument_tokens_and_start_tracking(self, user_id, trade_session_id, is_dummy):
                return None
            def is_running(self):
                return False
        class _CapFactory:
            def __init__(self):
                self.last_scanner = None
            def get_scanner(self, name, freq):
                self.last_scanner = _CapScanner()
                return self.last_scanner
        factory = _CapFactory()
        consumer._scanner_factory = factory

        # Capture routing and ack
        routed = {'called': False, 'is_resume': None}
        _orig = consumer._handle_scanner_event
        def _wrap(ev, is_resume=False):
            routed['called'] = True
            routed['is_resume'] = is_resume
            return _orig(ev, is_resume=is_resume)
        consumer._handle_scanner_event = _wrap

        acked = []

        # Act
        try:
            with patch('scanning_service.consumers.scanning_queue_consumer.IntegrationServiceProvider', return_value=object()), \
                 patch('scanning_service.consumers.scanning_queue_consumer.TMUServiceProvider', return_value=object()):
                messages = consumer.redis_consumer.read_from_stream(stream, count=10, block=500)
                if messages:
                    for _s, msgs in messages:
                        for message_id, fields in msgs:
                            success = consumer._process_event(fields)
                            if success:
                                consumer.redis_consumer.acknowledge_message(stream, message_id)
                                acked.append(message_id)

            # Assert routed and filled IDs via scanner.configure
            assert routed['called'] is True and routed['is_resume'] is True
            assert factory.last_scanner and factory.last_scanner.configure_called is True
            cfg = factory.last_scanner.configure_kwargs
            assert cfg.get('trade_freq') == '10-minute'
            assert cfg.get('trade_session_id') == 10 or str(cfg.get('trade_session_id')) == '10'
            assert str(cfg.get('user_id')) == str(test_user_id)

            # Lock created
            exists, owner = consumer.lock_manager.check_lock(1, '10-minute')
            assert exists is True and owner

            # Event acknowledged
            assert len(acked) == 1

            # DB invariants
            ts = TradeSession.objects.get(id=10)
            assert ts.status == 'started' and ts.is_active is True

        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestEndToEndResumeEventInvalidAlgorithm:
    """
    3.2 Case C – Invalid Resume (bad algorithm): non-existent scanning_algorithm_name.
    Expect: routed is_resume=True, returns False, no lock, no ack, no DB changes.
    """

    def test_resume_invalid_algorithm_no_lock_no_ack_no_db_changes(self, table_data_manager, redis_data_manager, test_user_id):
        # Arrange
        test_stream = f"scanning_queue_test_{uuid.uuid4().hex[:8]}"
        setattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', test_stream)
        stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(stream)

        table_data_manager.clear_table_completely('scanning_algorithms')
        table_data_manager.clear_table_completely('trade_sessions')

        consumer = ScanningQueueConsumer()
        assert consumer.redis_consumer.ensure_consumer_group(stream) is True
        try:
            consumer.lock_manager.redis_client.delete("scanner_lock:1:10-minute")
        except Exception:
            pass

        event = {
            'event_id': 'evt-resume-bad',
            'event_type': 'resume_scanner',
            'trading_frequency': '10-minute',
            'scanning_algorithm_name': 'UDTS',  # not seeded
            'is_dummy': '0'
        }
        redis_data_manager.insert_stream_data(stream, event)

        # Capture routing and ack
        routed = {'called': False, 'is_resume': None}
        _orig = consumer._handle_scanner_event
        def _wrap(ev, is_resume=False):
            routed['called'] = True
            routed['is_resume'] = is_resume
            return _orig(ev, is_resume=is_resume)
        consumer._handle_scanner_event = _wrap
        acked = []

        # Act
        try:
            messages = consumer.redis_consumer.read_from_stream(stream, count=10, block=500)
            if messages:
                for _s, msgs in messages:
                    for message_id, fields in msgs:
                        success = consumer._process_event(fields)
                        if success:
                            consumer.redis_consumer.acknowledge_message(stream, message_id)
                            acked.append(message_id)

            # Assert routing and failure
            assert routed['called'] is True and routed['is_resume'] is True
            exists, owner = consumer.lock_manager.check_lock(1, '10-minute')
            assert exists is False
            assert len(acked) == 0
            assert TradeSession.objects.count() == 0

        finally:
            try:
                consumer.redis_consumer.close()
            except Exception:
                pass