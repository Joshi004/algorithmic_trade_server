"""
Pytest configuration and fixtures for the ATS testing suite.

This file contains:
- Database fixtures for test isolation
- Factory fixtures for creating test data
- Utility fixtures for common testing operations
- Data snapshot utilities for SQL data handling
"""

import pytest
import uuid
from django.db import transaction
from django.test import override_settings
from django.core.management import call_command
from integration_service.models.UserBrokerCredential import UserBrokerCredential
from tests.utils.table_data_manager import TableDataManager
from tests.utils.redis_data_manager import RedisDataManager

import json
import os


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup that ensures test database is properly configured.
    This runs once per test session.
    """
    with django_db_blocker.unblock():
        # Run migrations to ensure all tables exist
        call_command('migrate', '--run-syncdb', verbosity=0)
        

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Enable database access for all tests automatically.
    This ensures test isolation by wrapping each test in a transaction.
    """
    pass


@pytest.fixture
def clean_db(db):
    """
    Provides a completely clean database for tests.
    Truncates all tables before each test that uses this fixture.
    """
    from django.core.management.color import no_style
    from django.db import connection
    
    style = no_style()
    sql = connection.ops.sql_flush(style, [UserBrokerCredential._meta.db_table])
    with connection.cursor() as cursor:
        for query in sql:
            cursor.execute(query)


@pytest.fixture
def test_user_id():
    """
    Provides a consistent test user ID for tests.
    """
    return uuid.uuid4()


@pytest.fixture
def sample_broker_credential_data(test_user_id):
    """
    Provides ASCII table data for a sample active broker credential.
    Use with table_data_manager.insert_table_data('user_broker_credentials', data)
    """
    return f"""
    +--------------------------------------+-------------+------------------+-------------------+--------+------------+
    | user_id                              | broker_name | api_key          | api_secret        | status | is_default |
    +--------------------------------------+-------------+------------------+-------------------+--------+------------+
    | {test_user_id}                       | zerodha     | test_api_key_123 | test_secret_456   | active | 1          |
    +--------------------------------------+-------------+------------------+-------------------+--------+------------+
    """


@pytest.fixture  
def pending_broker_credential_data(test_user_id):
    """
    Provides ASCII table data for a pending broker credential.
    Use with table_data_manager.insert_table_data('user_broker_credentials', data)
    """
    return f"""
    +--------------------------------------+-------------+------------------+-------------------+---------------------+------------+
    | user_id                              | broker_name | api_key          | api_secret        | status              | is_default |
    +--------------------------------------+-------------+------------------+-------------------+---------------------+------------+
    | {test_user_id}                       | zerodha     | test_pending_key | test_pending_sec  | pending_verification| 1          |
    +--------------------------------------+-------------+------------------+-------------------+---------------------+------------+
    """


@pytest.fixture
def authenticated_request_factory():
    """
    Provides a request factory that can create authenticated requests.
    """
    from django.test import RequestFactory
    
    class AuthenticatedRequestFactory(RequestFactory):
        def authenticated_get(self, path, user_id, **kwargs):
            request = self.get(path, **kwargs)
            request.user_data = {'public_id': user_id}
            return request
            
        def authenticated_post(self, path, user_id, data=None, **kwargs):
            request = self.post(path, data, **kwargs)
            request.user_data = {'public_id': user_id}
            return request
    
    return AuthenticatedRequestFactory()


@pytest.fixture
def table_data_manager():
    """
    Provides the table data manager for handling ASCII table format test data.
    """
    return TableDataManager()


@pytest.fixture
def redis_data_manager():
    """
    Provides the Redis data manager for handling Redis test data.
    """
    manager = RedisDataManager()
    yield manager
    # Cleanup after test
    manager.cleanup()


@pytest.fixture
def mock_kite_api():
    """
    Provides mock data for Kite API responses to avoid real API calls in tests.
    """
    return {
        'login_url': 'https://kite.trade/connect/login?api_key=test_api_key&v=3',
        'session_data': {
            'user_id': 'TEST123',
            'email': 'test@example.com',
            'user_name': 'Test User',
            'access_token': 'test_access_token_12345',
            'refresh_token': 'test_refresh_token_67890',
            'public_token': 'test_public_token_abcdef',
            'login_time': '2024-01-15 10:30:00',
            'exchanges': ['NSE', 'BSE'],
            'order_types': ['MARKET', 'LIMIT'],
            'products': ['CNC', 'MIS'],
            'user_shortname': 'TestUser',
            'user_type': 'individual',
            'avatar_url': 'https://example.com/avatar.jpg'
        },
        'profile_data': {
            'user_id': 'TEST123',
            'email': 'test@example.com',
            'user_name': 'Test User',
            'user_shortname': 'TestUser',
            'user_type': 'individual',
            'avatar_url': 'https://example.com/avatar.jpg',
            'broker': 'ZERODHA',
            'exchanges': ['NSE', 'BSE'],
            'order_types': ['MARKET', 'LIMIT'],
            'products': ['CNC', 'MIS']
        }
    }


@pytest.fixture
def api_credentials():
    """
    Provides test API credentials for broker testing.
    """
    return {
        'api_key': 'test_api_key_12345',
        'api_secret': 'test_api_secret_67890'
    }





# Markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration  
pytest.mark.slow = pytest.mark.slow
pytest.mark.requires_db = pytest.mark.requires_db
pytest.mark.requires_broker = pytest.mark.requires_broker 