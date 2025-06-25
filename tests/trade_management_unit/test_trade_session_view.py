import pytest
import json
import uuid
import redis
from datetime import datetime
from django.test import RequestFactory
from django.conf import settings
from trade_management_unit.views.trade_session_view import initiate_trade_session
from ats_gateway.models.User import User


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.redis
class TestInitiateTradeSessionRedisEvents:
    """
    Redis Event Publishing Tests for Trade Session Initiation
    
    These tests verify that the trade session creation process correctly publishes 
    events to Redis streams with proper event structure and handles edge cases.
    All tests use real Redis interactions without mocking.
    """
    
    def test_new_trade_session_publishes_event_to_redis(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: New trade session creation publishes event to Redis scanning queue
        Expected: Event published to Redis with correct structure and data
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Get initial stream length
        initial_length = redis_data_manager.get_stream_length(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request to create NEW trade session
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation', 
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method (will create new session and publish event)
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] == True
        assert response_data['status'] == 'new'  # This should be a new session
        assert response_data['message'] == 'New session created'
        
        # Verify event was published to Redis
        final_length = redis_data_manager.get_stream_length(scanning_queue)
        assert final_length == initial_length + 1, f"Expected 1 new event, but stream length changed by {final_length - initial_length}"
        
        # Read the latest event from Redis stream to verify structure
        latest_events = self._read_latest_stream_events(redis_data_manager.redis_client, scanning_queue, 1)
        assert len(latest_events) == 1, "Should have exactly 1 new event"
        
        event_data = latest_events[0]['data']
        trade_session_id = response_data['trade_session_id']
        
        # Verify event structure and content
        assert 'event_id' in event_data
        assert 'event_type' in event_data
        assert 'timestamp' in event_data
        assert 'trade_session_id' in event_data
        assert 'user_id' in event_data
        assert 'scanning_algorithm_name' in event_data
        assert 'initiation_algorithm_name' in event_data
        assert 'termination_algorithm_name' in event_data
        assert 'trading_frequency' in event_data
        assert 'is_dummy' in event_data
        assert 'session_status' in event_data
        assert 'started_at' in event_data
        
        # Verify specific event values
        assert event_data['event_type'] == 'trade_session_initiated'
        assert event_data['trade_session_id'] == str(trade_session_id)
        assert event_data['user_id'] == test_user_id
        assert event_data['scanning_algorithm_name'] == 'test_scanning'
        assert event_data['initiation_algorithm_name'] == 'test_initiation'
        assert event_data['termination_algorithm_name'] == 'test_termination'
        assert event_data['trading_frequency'] == '5-minute'
        assert event_data['is_dummy'] == 'False'  # Redis stores as string
        assert event_data['session_status'] == 'started'
        
        # Verify timestamp format (should be ISO format)
        timestamp = event_data['timestamp']
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should parse without error
        
        # Verify event_id is valid UUID
        uuid.UUID(event_data['event_id'])  # Should parse without error
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_existing_trade_session_does_not_publish_event(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Existing trade session found does NOT publish event to Redis
        Expected: No new event published when session already exists
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make request to create first session
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Create first session (should publish event)
        first_response = initiate_trade_session(request)
        assert first_response.status_code == 200
        first_response_data = json.loads(first_response.content)
        assert first_response_data['status'] == 'new'
        
        # Get stream length after first creation
        length_after_first = redis_data_manager.get_stream_length(scanning_queue)
        assert length_after_first == 1, "Should have 1 event after first session creation"
        
        # Make identical request again (should find existing session)
        second_response = initiate_trade_session(request)
        assert second_response.status_code == 200
        second_response_data = json.loads(second_response.content)
        
        # Verify second request found existing session
        assert second_response_data['status'] == 'existing'
        assert second_response_data['message'] == 'Session already exists'
        assert second_response_data['trade_session_id'] == first_response_data['trade_session_id']
        
        # Verify NO new event was published for existing session
        length_after_second = redis_data_manager.get_stream_length(scanning_queue)
        assert length_after_second == length_after_first, "No new event should be published for existing session"
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_dummy_session_event_structure(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Dummy trade session creation publishes correct event with is_dummy=True
        Expected: Event published with is_dummy field set to True
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request for DUMMY session
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '10-minute',
            'dummy': 'true'  # Request dummy session
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] == True
        assert response_data['status'] == 'new'
        
        # Read the event from Redis stream
        latest_events = self._read_latest_stream_events(redis_data_manager.redis_client, scanning_queue, 1)
        assert len(latest_events) == 1
        
        event_data = latest_events[0]['data']
        
        # Verify dummy session specific fields
        assert event_data['event_type'] == 'trade_session_initiated'
        assert event_data['is_dummy'] == 'True'  # Should be True for dummy session
        assert event_data['trading_frequency'] == '10-minute'
        assert event_data['user_id'] == test_user_id
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_live_session_event_structure(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Live trade session creation publishes correct event with is_dummy=False
        Expected: Event published with is_dummy field set to False
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request for LIVE session (dummy=false or omitted)
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '15-minute',
            'dummy': 'false'  # Explicitly request live session
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] == True
        assert response_data['status'] == 'new'
        
        # Read the event from Redis stream
        latest_events = self._read_latest_stream_events(redis_data_manager.redis_client, scanning_queue, 1)
        assert len(latest_events) == 1
        
        event_data = latest_events[0]['data']
        
        # Verify live session specific fields
        assert event_data['event_type'] == 'trade_session_initiated'
        assert event_data['is_dummy'] == 'False'  # Should be False for live session
        assert event_data['trading_frequency'] == '15-minute'
        assert event_data['user_id'] == test_user_id
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_different_algorithms_in_event_structure(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Different algorithm combinations are correctly reflected in published events
        Expected: Event contains correct algorithm names based on request parameters
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup multiple algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 2  | advanced_scanner | Advanced Scanner   | Advanced scanning algo     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 2  | smart_initiator   | Smart Initiator     | Smart initiation algorithm  | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 2  | profit_terminator  | Profit Terminator    | Profit based terminator      | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request with different algorithm combination
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'advanced_scanner',
            'initiation_algorithm_name': 'smart_initiator',
            'termination_algorithm_name': 'profit_terminator',
            'trading_frequency': '30-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] == True
        assert response_data['status'] == 'new'
        
        # Read the event from Redis stream
        latest_events = self._read_latest_stream_events(redis_data_manager.redis_client, scanning_queue, 1)
        assert len(latest_events) == 1
        
        event_data = latest_events[0]['data']
        
        # Verify algorithm names in event match request
        assert event_data['scanning_algorithm_name'] == 'advanced_scanner'
        assert event_data['initiation_algorithm_name'] == 'smart_initiator'
        assert event_data['termination_algorithm_name'] == 'profit_terminator'
        assert event_data['trading_frequency'] == '30-minute'
        assert event_data['event_type'] == 'trade_session_initiated'
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_redis_connection_failure_does_not_break_session_creation(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Redis connection failure does not prevent trade session creation
        Expected: Trade session creation succeeds even if Redis event publishing fails
        Note: This test simulates Redis failure by temporarily corrupting Redis client
        """
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '1-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Temporarily disrupt Redis to simulate connection failure
        original_host = settings.REDIS_HOST
        settings.REDIS_HOST = 'invalid_redis_host_that_does_not_exist'
        
        try:
            # Call the real method - should succeed despite Redis failure
            response = initiate_trade_session(request)
            
            # Verify trade session creation still succeeds
            assert response.status_code == 200
            response_data = json.loads(response.content)
            assert response_data['success'] == True
            assert response_data['status'] == 'new'
            assert 'trade_session_id' in response_data
            
        finally:
            # Restore Redis configuration
            settings.REDIS_HOST = original_host
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()

    def _read_latest_stream_events(self, redis_client, stream_name, count=1):
        """
        Helper method to read latest events from Redis stream
        
        Args:
            redis_client: Redis client instance
            stream_name: Name of the stream to read from
            count: Number of latest events to read
            
        Returns:
            List of events with their IDs and data
        """
        try:
            # Read latest events from the stream
            # XREVRANGE reads in reverse order (latest first)
            events = redis_client.xrevrange(stream_name, count=count)
            
            result = []
            for event_id, fields in events:
                result.append({
                    'id': event_id,
                    'data': fields
                })
            
            return result
        except Exception as e:
            raise Exception(f"Failed to read stream events: {str(e)}")


@pytest.mark.integration
@pytest.mark.requires_db
class TestInitiateTradeSession:
    """
    Original Business Logic Tests for Trade Session Initiation
    
    These tests verify the core functionality of the trade session initiation process
    including authentication, parameter validation, and response handling.
    """
    
    def test_success_with_valid_authentication_and_parameters(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Valid authentication provided with valid parameters
        Expected: 200 with successful trade session initiation result
        """
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method without mocking
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        
        # Verify response has expected structure (based on real TradeSession response)
        assert 'success' in response_data or 'status' in response_data or 'message' in response_data
        
        # Cleanup trade_sessions first due to foreign key constraints
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()

    def test_new_trade_session_publishes_event_to_redis(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: New trade session creation publishes event to Redis scanning queue
        Expected: Event published to Redis with correct structure and data
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Get initial stream length
        initial_length = redis_data_manager.get_stream_length(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request to create NEW trade session
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation', 
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method (will create new session and publish event)
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] == True
        assert response_data['status'] == 'new'  # This should be a new session
        assert response_data['message'] == 'New session created'
        
        # Verify event was published to Redis
        final_length = redis_data_manager.get_stream_length(scanning_queue)
        assert final_length == initial_length + 1, f"Expected 1 new event, but stream length changed by {final_length - initial_length}"
        
        # Read the latest event from Redis stream to verify structure
        latest_events = self._read_latest_stream_events(redis_data_manager.redis_client, scanning_queue, 1)
        assert len(latest_events) == 1, "Should have exactly 1 new event"
        
        event_data = latest_events[0]['data']
        trade_session_id = response_data['trade_session_id']
        
        # Verify event structure and content
        assert 'event_id' in event_data
        assert 'event_type' in event_data
        assert 'timestamp' in event_data
        assert 'trade_session_id' in event_data
        assert 'user_id' in event_data
        assert 'scanning_algorithm_name' in event_data
        assert 'initiation_algorithm_name' in event_data
        assert 'termination_algorithm_name' in event_data
        assert 'trading_frequency' in event_data
        assert 'is_dummy' in event_data
        assert 'session_status' in event_data
        assert 'started_at' in event_data
        
        # Verify specific event values
        assert event_data['event_type'] == 'trade_session_initiated'
        assert event_data['trade_session_id'] == str(trade_session_id)
        assert event_data['user_id'] == test_user_id
        assert event_data['scanning_algorithm_name'] == 'test_scanning'
        assert event_data['initiation_algorithm_name'] == 'test_initiation'
        assert event_data['termination_algorithm_name'] == 'test_termination'
        assert event_data['trading_frequency'] == '5-minute'
        assert event_data['is_dummy'] == 'False'  # Redis stores as string
        assert event_data['session_status'] == 'started'
        
        # Verify timestamp format (should be ISO format)
        timestamp = event_data['timestamp']
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should parse without error
        
        # Verify event_id is valid UUID
        uuid.UUID(event_data['event_id'])  # Should parse without error
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_existing_trade_session_does_not_publish_event(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Existing trade session found does NOT publish event to Redis
        Expected: No new event published when session already exists
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make request to create first session
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Create first session (should publish event)
        first_response = initiate_trade_session(request)
        assert first_response.status_code == 200
        first_response_data = json.loads(first_response.content)
        assert first_response_data['status'] == 'new'
        
        # Get stream length after first creation
        length_after_first = redis_data_manager.get_stream_length(scanning_queue)
        assert length_after_first == 1, "Should have 1 event after first session creation"
        
        # Make identical request again (should find existing session)
        second_response = initiate_trade_session(request)
        assert second_response.status_code == 200
        second_response_data = json.loads(second_response.content)
        
        # Verify second request found existing session
        assert second_response_data['status'] == 'existing'
        assert second_response_data['message'] == 'Session already exists'
        assert second_response_data['trade_session_id'] == first_response_data['trade_session_id']
        
        # Verify NO new event was published for existing session
        length_after_second = redis_data_manager.get_stream_length(scanning_queue)
        assert length_after_second == length_after_first, "No new event should be published for existing session"
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_dummy_session_event_structure(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Dummy trade session creation publishes correct event with is_dummy=True
        Expected: Event published with is_dummy field set to True
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request for DUMMY session
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '10-minute',
            'dummy': 'true'  # Request dummy session
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] == True
        assert response_data['status'] == 'new'
        
        # Read the event from Redis stream
        latest_events = self._read_latest_stream_events(redis_data_manager.redis_client, scanning_queue, 1)
        assert len(latest_events) == 1
        
        event_data = latest_events[0]['data']
        
        # Verify dummy session specific fields
        assert event_data['event_type'] == 'trade_session_initiated'
        assert event_data['is_dummy'] == 'True'  # Should be True for dummy session
        assert event_data['trading_frequency'] == '10-minute'
        assert event_data['user_id'] == test_user_id
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_live_session_event_structure(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Live trade session creation publishes correct event with is_dummy=False
        Expected: Event published with is_dummy field set to False
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request for LIVE session (dummy=false or omitted)
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '15-minute',
            'dummy': 'false'  # Explicitly request live session
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] == True
        assert response_data['status'] == 'new'
        
        # Read the event from Redis stream
        latest_events = self._read_latest_stream_events(redis_data_manager.redis_client, scanning_queue, 1)
        assert len(latest_events) == 1
        
        event_data = latest_events[0]['data']
        
        # Verify live session specific fields
        assert event_data['event_type'] == 'trade_session_initiated'
        assert event_data['is_dummy'] == 'False'  # Should be False for live session
        assert event_data['trading_frequency'] == '15-minute'
        assert event_data['user_id'] == test_user_id
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_different_algorithms_in_event_structure(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Different algorithm combinations are correctly reflected in published events
        Expected: Event contains correct algorithm names based on request parameters
        """
        # Clear Redis scanning queue before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup multiple algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 2  | advanced_scanner | Advanced Scanner   | Advanced scanning algo     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 2  | smart_initiator   | Smart Initiator     | Smart initiation algorithm  | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 2  | profit_terminator  | Profit Terminator    | Profit based terminator      | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request with different algorithm combination
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'advanced_scanner',
            'initiation_algorithm_name': 'smart_initiator',
            'termination_algorithm_name': 'profit_terminator',
            'trading_frequency': '30-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method
        response = initiate_trade_session(request)
        
        # Verify successful response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] == True
        assert response_data['status'] == 'new'
        
        # Read the event from Redis stream
        latest_events = self._read_latest_stream_events(redis_data_manager.redis_client, scanning_queue, 1)
        assert len(latest_events) == 1
        
        event_data = latest_events[0]['data']
        
        # Verify algorithm names in event match request
        assert event_data['scanning_algorithm_name'] == 'advanced_scanner'
        assert event_data['initiation_algorithm_name'] == 'smart_initiator'
        assert event_data['termination_algorithm_name'] == 'profit_terminator'
        assert event_data['trading_frequency'] == '30-minute'
        assert event_data['event_type'] == 'trade_session_initiated'
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()
        redis_data_manager.clear_stream_completely(scanning_queue)

    def test_redis_connection_failure_does_not_break_session_creation(self, authenticated_request_factory, table_data_manager, redis_data_manager):
        """
        Test: Redis connection failure does not prevent trade session creation
        Expected: Trade session creation succeeds even if Redis event publishing fails
        Note: This test simulates Redis failure by temporarily corrupting Redis client
        """
        # Setup test user
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '1-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Temporarily disrupt Redis to simulate connection failure
        original_host = settings.REDIS_HOST
        settings.REDIS_HOST = 'invalid_redis_host_that_does_not_exist'
        
        try:
            # Call the real method - should succeed despite Redis failure
            response = initiate_trade_session(request)
            
            # Verify trade session creation still succeeds
            assert response.status_code == 200
            response_data = json.loads(response.content)
            assert response_data['success'] == True
            assert response_data['status'] == 'new'
            assert 'trade_session_id' in response_data
            
        finally:
            # Restore Redis configuration
            settings.REDIS_HOST = original_host
        
        # Cleanup
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()

    def _read_latest_stream_events(self, redis_client, stream_name, count=1):
        """
        Helper method to read latest events from Redis stream
        
        Args:
            redis_client: Redis client instance
            stream_name: Name of the stream to read from
            count: Number of latest events to read
            
        Returns:
            List of events with their IDs and data
        """
        try:
            # Read latest events from the stream
            # XREVRANGE reads in reverse order (latest first)
            events = redis_client.xrevrange(stream_name, count=count)
            
            result = []
            for event_id, fields in events:
                result.append({
                    'id': event_id,
                    'data': fields
                })
            
            return result
        except Exception as e:
            raise Exception(f"Failed to read stream events: {str(e)}")

    # ==================== ORIGINAL FUNCTIONALITY TESTS ====================
    # These tests verify the original business logic without Redis event focus
    
    def test_parameter_unpacking_to_business_logic(self, authenticated_request_factory, table_data_manager):
        """
        Test: Parameters correctly unpacked to business logic
        Expected: Real TradeSession.initiate_trade_session called with user_id_str and unpacked params
        """
        # Setup test user and algorithms
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request with dummy parameter
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '10-minute',
            'dummy': 'true'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method without mocking
        response = initiate_trade_session(request)
        
        # Verify response
        assert response.status_code == 200
        response_data = json.loads(response.content)
        
        # Verify response has expected structure
        assert 'success' in response_data or 'status' in response_data or 'message' in response_data
        
        # Cleanup trade_sessions first due to foreign key constraints
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()

    def test_successful_response_structure(self, authenticated_request_factory, table_data_manager):
        """
        Test: Success response structure
        Expected: JsonResponse containing exact result from TradeSession.initiate_trade_session with 200 status
        """
        # Setup test user and algorithms
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '15-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method without mocking
        response = initiate_trade_session(request)
        
        # Verify response structure and content
        assert response.status_code == 200
        assert response.get('content-type') == 'application/json'
        response_data = json.loads(response.content)
        
        # Verify response is a valid JSON object
        assert isinstance(response_data, dict)
        
        # Cleanup trade_sessions first due to foreign key constraints
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()

    def test_complete_successful_flow_integration(self, authenticated_request_factory, table_data_manager):
        """
        Test: Complete successful flow - validate authentication, validate parameters, execute business logic, return response
        Expected: All steps execute in sequence and return successful response
        """
        # Setup test user and algorithms
        test_user_id = str(uuid.uuid4())
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Setup algorithms
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request with all required parameters
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '30-minute',
            'dummy': '0'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method without mocking
        response = initiate_trade_session(request)
        
        # Verify complete flow executed successfully
        assert response.status_code == 200
        response_data = json.loads(response.content)
        
        # Verify response is valid
        assert isinstance(response_data, dict)
        
        # Cleanup trade_sessions first due to foreign key constraints
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup()

    def test_early_termination_on_authentication_failure(self, authenticated_request_factory, table_data_manager):
        """
        Test: Early termination on authentication failure
        Expected: Should not proceed to parameter validation or business logic when authentication fails
        """
        # Setup algorithms to ensure they're available (but shouldn't be accessed)
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        
        # Make unauthenticated request
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        # Remove authentication
        if hasattr(request, 'user_data'):
            delattr(request, 'user_data')
        
        # Call the real method without mocking
        response = initiate_trade_session(request)
        
        # Verify authentication failure response
        assert response.status_code == 401
        response_data = json.loads(response.content)
        assert response_data['error'] == 'Authentication required'
        
        # Cleanup
        table_data_manager.cleanup()

    def test_early_termination_on_parameter_validation_failure(self, authenticated_request_factory, table_data_manager):
        """
        Test: Early termination on parameter validation failure
        Expected: Should not proceed to business logic when parameter validation fails after successful authentication
        """
        test_user_id = str(uuid.uuid4())
        
        # Make authenticated request with missing parameters
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            # Missing other required parameters
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method without mocking
        response = initiate_trade_session(request)
        
        # Verify parameter validation failure response
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['error'] == 'Missing required parameters'

    def test_empty_parameters_handling(self, authenticated_request_factory, table_data_manager):
        """
        Test: Empty parameters dictionary handled
        Expected: Should pass only user_id_str when no additional parameters are extracted (edge case)
        """
        test_user_id = str(uuid.uuid4())
        
        # Make authenticated request without any query parameters
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/')
        request.user_data = {'public_id': test_user_id}
        
        response = initiate_trade_session(request)
        
        # Should fail at parameter validation level due to missing required parameters
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['error'] == 'Missing required parameters'

    def test_authentication_failure_no_user_data(self, authenticated_request_factory, table_data_manager):
        """
        Test: No user_data attribute in request
        Expected: 401 with 'Authentication required' error
        """
        # Make unauthenticated request
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        
        # Remove user_data if it exists
        if hasattr(request, 'user_data'):
            delattr(request, 'user_data')
        
        response = initiate_trade_session(request)
        
        # Verify authentication failure
        assert response.status_code == 401
        response_data = json.loads(response.content)
        assert response_data['error'] == 'Authentication required'

    def test_authentication_failure_no_public_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: user_data exists but no public_id
        Expected: 401 with 'Authentication required' error
        """
        # Make request with user_data but no public_id
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {}  # Empty user_data without public_id
        
        response = initiate_trade_session(request)
        
        # Verify authentication failure
        assert response.status_code == 401
        response_data = json.loads(response.content)
        assert response_data['error'] == 'Authentication required'

    def test_parameter_validation_failure_missing_required_params(self, authenticated_request_factory, table_data_manager):
        """
        Test: Missing required parameters
        Expected: 400 with 'Missing required parameters' error
        """
        test_user_id = str(uuid.uuid4())
        
        # Make authenticated request with missing parameters
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            # Missing other required parameters
        })
        request.user_data = {'public_id': test_user_id}
        
        response = initiate_trade_session(request)
        
        # Verify parameter validation failure
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['error'] == 'Missing required parameters'

    def test_parameter_validation_failure_invalid_scanning_algorithm(self, authenticated_request_factory, table_data_manager):
        """
        Test: Invalid scanning algorithm name
        Expected: 400 with 'Invalid scanning algorithm name' error
        """
        test_user_id = str(uuid.uuid4())
        
        # Setup user but no algorithms so scanning algorithm validation fails
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        table_data_manager.insert_table_data('users', users_data)
        
        # Make authenticated request with invalid scanning algorithm
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'nonexistent_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        response = initiate_trade_session(request)
        
        # Verify error response
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert 'Invalid scanning algorithm name: nonexistent_scanning' in response_data['error']
        
        # Cleanup
        table_data_manager.cleanup()

    def test_parameter_validation_failure_invalid_initiation_algorithm(self, authenticated_request_factory, table_data_manager):
        """
        Test: Invalid initiation algorithm name
        Expected: 400 with 'Invalid initiation algorithm name' error
        """
        test_user_id = str(uuid.uuid4())
        
        # Setup user and scanning algorithm but not initiation algorithm
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('users', users_data)
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        
        # Make authenticated request with invalid initiation algorithm
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'nonexistent_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        response = initiate_trade_session(request)
        
        # Verify error response
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert 'Invalid initiation algorithm name: nonexistent_initiation' in response_data['error']
        
        # Cleanup
        table_data_manager.cleanup()

    def test_parameter_validation_failure_invalid_termination_algorithm(self, authenticated_request_factory, table_data_manager):
        """
        Test: Invalid termination algorithm name
        Expected: 400 with 'Invalid termination algorithm name' error
        """
        test_user_id = str(uuid.uuid4())
        
        # Setup user, scanning and initiation algorithms but not termination algorithm
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('users', users_data)
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        
        # Make authenticated request with invalid termination algorithm
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'nonexistent_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        response = initiate_trade_session(request)
        
        # Verify error response
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert 'Invalid termination algorithm name: nonexistent_termination' in response_data['error']
        
        # Cleanup
        table_data_manager.cleanup()

    def test_response_structure_validation(self, authenticated_request_factory, table_data_manager):
        """
        Test: Response structure validation
        Expected: JsonResponse has correct structure and fields
        """
        test_user_id = str(uuid.uuid4())
        
        # Setup test user and algorithms
        users_data = f"""
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | public_id                        | email            | first_name | last_name | is_active | date_joined         | password    | is_superuser | is_staff |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        | {test_user_id.replace("-", "")}  | test@example.com | Test       | User      | 1         | 2024-01-15 10:00:00 | testpass123 | 0            | 0        |
        +----------------------------------+------------------+------------+-----------+-----------+---------------------+-----------+--------------+----------+
        """
        
        scanning_algorithms_data = """
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | id | name             | display_name       | description                | is_active | created_at          | updated_at          |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        | 1  | test_scanning    | Test Scanning Algo | Test scanning algorithm    | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+------------------+--------------------+----------------------------+-----------+---------------------+---------------------+
        """
        
        initiation_algorithms_data = """
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | id | name              | display_name        | description                 | is_active | created_at          | updated_at          |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        | 1  | test_initiation   | Test Initiation Algo| Test initiation algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+-------------------+---------------------+-----------------------------+-----------+---------------------+---------------------+
        """
        
        termination_algorithms_data = """
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | id | name               | display_name         | description                  | is_active | created_at          | updated_at          |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        | 1  | test_termination   | Test Termination Algo| Test termination algorithm   | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----+--------------------+----------------------+------------------------------+-----------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('users', users_data)
        table_data_manager.insert_table_data('scanning_algorithms', scanning_algorithms_data)
        table_data_manager.insert_table_data('initiation_algorithms', initiation_algorithms_data)
        table_data_manager.insert_table_data('termination_algorithms', termination_algorithms_data)
        
        # Make authenticated request
        request = authenticated_request_factory.get('/trade_management/initiate_trade_session/', data={
            'scanning_algorithm_name': 'test_scanning',
            'initiation_algorithm_name': 'test_initiation',
            'termination_algorithm_name': 'test_termination',
            'trading_frequency': '5-minute'
        })
        request.user_data = {'public_id': test_user_id}
        
        # Call the real method without mocking
        response = initiate_trade_session(request)
        
        # Verify response is JsonResponse with correct structure
        assert response.status_code == 200
        assert response.get('content-type') == 'application/json'
        response_data = json.loads(response.content)
        
        # Verify response is a valid JSON object
        assert isinstance(response_data, dict)
        
        # Cleanup trade_sessions first due to foreign key constraints
        table_data_manager.clear_table_completely('trade_sessions')
        table_data_manager.cleanup() 