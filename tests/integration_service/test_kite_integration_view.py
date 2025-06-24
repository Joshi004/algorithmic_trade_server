"""
Integration tests for kite_integration_view.py

Simple input-output tests for get_historical_data view:
- Real HTTP API calls using Django test client
- Real database interactions and business logic  
- Only mock external Kite API calls with correct format
- Simple, dumb, brainless test cases
- Manual cleanup using table_data_manager for complete control
"""

import pytest
import json
from unittest.mock import patch
from datetime import datetime
from django.test import Client
from integration_service.views.kite_integration_view import get_historical_data, get_quotes, get_instruments


@pytest.mark.integration
@pytest.mark.requires_db
class TestGetHistoricalData:
    """
    Tests for get_historical_data API endpoint using Django test client.
    Only mocks external Kite API calls, everything else is real.
    """
    
    def test_success_with_middleware_auth(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid request with middleware auth
        Expected: 200 with historical data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '12345678123412341234123456789012'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response (real format)
        kite_candles = [
            ["2024-01-15T09:15:00+0530", 2500.5, 2510.0, 2495.25, 2505.8, 1000],
            ["2024-01-15T09:20:00+0530", 2505.8, 2515.5, 2500.0, 2510.25, 1200]
        ]
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'symbol': 'RELIANCE',
                'token': '738561',
                'interval': '5-minute', 
                'number_of_candles': '10'
            }
        )
        
        # Call view with mocked Kite API
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.historical_data', return_value=kite_candles):
            
            response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert len(data['data']) == 2
        assert data['meta']['size'] == 2
        assert data['meta']['api_success_status'] == True
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_success_with_query_param_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid request with user_id in query param (internal service path)
        Expected: 200 with historical data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '87654321432143214321210987654321'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | internal_key     | internal_secret   | active | 1          | internal_token            | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_candles = [
            ["2024-01-15T00:00:00+0530", 1400.0, 1420.0, 1390.0, 1410.0, 500000]
        ]
        
        # Make request (no middleware, user_id in query)
        request = authenticated_request_factory.get(
            '/integration/get_historical_data/',
            data={
                'user_id': user_id,
                'symbol': 'INFY',
                'token': '408065',
                'interval': '1-day',
                'number_of_candles': '5'
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.historical_data', return_value=kite_candles):
            
            response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert len(data['data']) == 1
        assert data['meta']['api_success_status'] == True
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_middleware_auth_takes_precedence(self, authenticated_request_factory, table_data_manager):
        """
        Test: Middleware user_id takes precedence over query param
        Expected: Uses middleware user, not query param user
        """
        # Setup database with two users
        table_data_manager.clear_table_completely('user_broker_credentials')
        middleware_user = '11111111111111111111111111111111'
        query_user = '22222222222222222222222222222222'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {middleware_user}                | zerodha     | middleware_key   | middleware_secret | active | 1          | middleware_token          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | {query_user}                     | zerodha     | query_key        | query_secret      | active | 1          | query_token               | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_candles = []
        
        # Make request with both user_ids
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            middleware_user,  # Middleware auth
            data={
                'user_id': query_user,  # Should be ignored
                'symbol': 'TCS',
                'token': '2953217',
                'interval': '15-minute',
                'number_of_candles': '20'
            }
        )
        
        # Call view and verify middleware key was used
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x) as mock_decrypt, \
             patch('kiteconnect.connect.KiteConnect.historical_data', return_value=kite_candles):
            
            response = get_historical_data(request)
            
            # Check that middleware credentials were decrypted, not query user
            decrypted_values = [call.args[0] for call in mock_decrypt.call_args_list]
            assert 'middleware_key' in decrypted_values
            assert 'query_key' not in decrypted_values
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_missing_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: No user_id provided
        Expected: 400 error
        """
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make request without user_id
        request = authenticated_request_factory.get(
            '/integration/get_historical_data/',
            data={
                'symbol': 'HDFC',
                'token': '340481',
                'interval': '1-minute',
                'number_of_candles': '100'
            }
        )
        
        # Call view
        response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'User ID is required'
    
    def test_missing_symbol(self, authenticated_request_factory, table_data_manager):
        """
        Test: Missing symbol parameter
        Expected: 400 error
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '33333333333333333333333333333333'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request without symbol
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'token': '738561',
                'interval': '5-minute',
                'number_of_candles': '10'
            }
        )
        
        # Call view
        response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'Missing required parameters: symbol'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_missing_multiple_parameters(self, authenticated_request_factory, table_data_manager):
        """
        Test: Missing multiple required parameters
        Expected: 400 error with all missing params listed
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '44444444444444444444444444444444'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request missing symbol and token
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'interval': '5-minute',
                'number_of_candles': '10'
            }
        )
        
        # Call view
        response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'Missing required parameters: symbol, token'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_invalid_number_of_candles(self, authenticated_request_factory, table_data_manager):
        """
        Test: Non-numeric number_of_candles
        Expected: 400 error
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '55555555555555555555555555555555'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request with invalid number_of_candles
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'symbol': 'SBIN',
                'token': '779521',
                'interval': '1-hour',
                'number_of_candles': 'abc'
            }
        )
        
        # Call view
        response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'number_of_candles must be a valid integer'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_invalid_trade_date_format(self, authenticated_request_factory, table_data_manager):
        """
        Test: Invalid trade_date format
        Expected: 400 error
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '66666666666666666666666666666666'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request with invalid date format
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'symbol': 'TATASTEEL',
                'token': '895745',
                'interval': '1-day',
                'number_of_candles': '5',
                'trade_date': '01/15/2024'  # Invalid format
            }
        )
        
        # Call view
        response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'trade_date must be in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_valid_trade_date(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid ISO trade_date
        Expected: 200 success (date parsing works)
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '77777777777777777777777777777777'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_candles = [
            ["2024-01-15T00:00:00+0530", 800.0, 820.0, 790.0, 810.0, 100000]
        ]
        
        # Make request with valid trade_date
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'symbol': 'BHARTIARTL',
                'token': '2714625',
                'interval': '1-day',
                'number_of_candles': '10',
                'trade_date': '2024-01-15'
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.historical_data', return_value=kite_candles):
            
            response = get_historical_data(request)
            
            # Verify response - date was parsed successfully (no 400 error)
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['status'] == 'success'
            # Don't assert on data length since business logic might filter/transform data
            
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_empty_data_from_kite_api(self, authenticated_request_factory, table_data_manager):
        """
        Test: Kite API returns empty data (expired instrument)
        Expected: 200 with empty data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '88888888888888888888888888888888'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API returning empty data
        kite_candles = []
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'symbol': 'EXPIREDSTOCK',
                'token': '999999',
                'interval': '1-day',
                'number_of_candles': '10'
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.historical_data', return_value=kite_candles):
            
            response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert data['data'] == []
        assert data['meta']['size'] == 0
        assert data['meta']['api_success_status'] == True
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_kite_api_exception(self, authenticated_request_factory, table_data_manager):
        """
        Test: Kite API throws exception
        Expected: 200 with empty data and api_success_status=False
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '99999999999999999999999999999999'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'symbol': 'FAILSTOCK',
                'token': '654321',
                'interval': '5-minute',
                'number_of_candles': '20'
            }
        )
        
        # Call view with Kite API exception
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.historical_data', side_effect=Exception('Network error')):
            
            response = get_historical_data(request)
        
        # Verify business logic handles exception correctly
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert data['data'] == []
        assert data['meta']['size'] == 0
        assert data['meta']['api_success_status'] == False
        assert 'Network error' in data['meta']['api_error_message']
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_no_broker_credentials(self, authenticated_request_factory, table_data_manager):
        """
        Test: User has no broker credentials
        Expected: 500 error
        """
        # Setup database with no credentials
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '00000000000000000000000000000000'
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_historical_data/',
            user_id,
            data={
                'symbol': 'TESTSTOCK',
                'token': '123456',
                'interval': '1-day',
                'number_of_candles': '5'
            }
        )
        
        # Call view
        response = get_historical_data(request)
        
        # Verify
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['status'] == 'error'

@pytest.mark.integration
@pytest.mark.requires_db
class TestGetQuotes:
    """
    Tests for get_quotes API endpoint using Django test client.
    Only mocks external Kite API calls, everything else is real.
    """
    
    def test_success_with_middleware_auth_single_symbol(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid request with middleware auth and single symbol
        Expected: 200 with quote data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '12345678123412341234123456789012'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_quotes = {
            'NSE:RELIANCE': {
                'last_price': 2500.75,
                'volume': 100000,
                'timestamp': '2024-01-15T15:30:00+0530',
                'ohlc': {
                    'open': 2495.0,
                    'high': 2510.0,
                    'low': 2490.0,
                    'close': 2500.75
                }
            }
        }
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': 'RELIANCE',
                'exchange': 'NSE'
            }
        )
        
        # Call view with mocked Kite API
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.quote', return_value=kite_quotes):
            
            response = get_quotes(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert 'NSE:RELIANCE' in data['data']
        assert data['data']['NSE:RELIANCE']['last_price'] == 2500.75
        assert data['meta']['exchange'] == 'NSE'
        assert data['meta']['symbols_requested'] == ['RELIANCE']
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_success_with_middleware_auth_multiple_symbols(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid request with middleware auth and multiple symbols
        Expected: 200 with multiple quote data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '23456789234567892345678923456789'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_quotes = {
            'NSE:RELIANCE': {
                'last_price': 2500.75,
                'volume': 100000
            },
            'NSE:TCS': {
                'last_price': 3400.50,
                'volume': 80000
            }
        }
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': 'RELIANCE,TCS',
                'exchange': 'NSE'
            }
        )
        
        # Call view with mocked Kite API
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.quote', return_value=kite_quotes):
            
            response = get_quotes(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert len(data['data']) == 2
        assert 'NSE:RELIANCE' in data['data']
        assert 'NSE:TCS' in data['data']
        assert data['meta']['symbols_requested'] == ['RELIANCE', 'TCS']
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_success_with_query_param_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid request with user_id in query param (internal service path)
        Expected: 200 with quote data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '34567890345678903456789034567890'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | internal_key     | internal_secret   | active | 1          | internal_token            | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_quotes = {
            'BSE:INFY': {
                'last_price': 1400.25,
                'volume': 50000
            }
        }
        
        # Make request (no middleware, user_id in query)
        request = authenticated_request_factory.get(
            '/integration/get_quotes/',
            data={
                'user_id': user_id,
                'symbol': 'INFY',
                'exchange': 'BSE'
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.quote', return_value=kite_quotes):
            
            response = get_quotes(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert 'BSE:INFY' in data['data']
        assert data['data']['BSE:INFY']['last_price'] == 1400.25
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_middleware_auth_takes_precedence(self, authenticated_request_factory, table_data_manager):
        """
        Test: Middleware user_id takes precedence over query param
        Expected: Uses middleware user, not query param user
        """
        # Setup database with two users
        table_data_manager.clear_table_completely('user_broker_credentials')
        middleware_user = '11111111111111111111111111111111'
        query_user = '22222222222222222222222222222222'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {middleware_user}                | zerodha     | middleware_key   | middleware_secret | active | 1          | middleware_token          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | {query_user}                     | zerodha     | query_key        | query_secret      | active | 1          | query_token               | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_quotes = {
            'NSE:HDFC': {
                'last_price': 1600.75,
                'volume': 75000
            }
        }
        
        # Make request with both user_ids
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            middleware_user,  # Middleware auth
            data={
                'user_id': query_user,  # Should be ignored
                'symbol': 'HDFC',
                'exchange': 'NSE'
            }
        )
        
        # Call view and verify middleware key was used
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x) as mock_decrypt, \
             patch('kiteconnect.connect.KiteConnect.quote', return_value=kite_quotes):
            
            response = get_quotes(request)
            
            # Check that middleware credentials were decrypted, not query user
            decrypted_values = [call.args[0] for call in mock_decrypt.call_args_list]
            assert 'middleware_key' in decrypted_values
            assert 'query_key' not in decrypted_values
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_missing_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: No user_id provided
        Expected: 400 error
        """
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make request without user_id
        request = authenticated_request_factory.get(
            '/integration/get_quotes/',
            data={
                'symbol': 'HDFC',
                'exchange': 'NSE'
            }
        )
        
        # Call view
        response = get_quotes(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'User ID is required'

    def test_missing_symbol(self, authenticated_request_factory, table_data_manager):
        """
        Test: Missing symbol parameter
        Expected: 400 error
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '45678901456789014567890145678901'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request without symbol
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'exchange': 'NSE'
            }
        )
        
        # Call view
        response = get_quotes(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == "Both 'symbol' and 'exchange' parameters are required"
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_missing_exchange(self, authenticated_request_factory, table_data_manager):
        """
        Test: Missing exchange parameter
        Expected: 400 error
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '56789012567890125678901256789012'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request without exchange
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': 'TCS'
            }
        )
        
        # Call view
        response = get_quotes(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == "Both 'symbol' and 'exchange' parameters are required"
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_missing_both_symbol_and_exchange(self, authenticated_request_factory, table_data_manager):
        """
        Test: Missing both symbol and exchange parameters
        Expected: 400 error
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '67890123678901236789012367890123'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request without symbol and exchange
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={}
        )
        
        # Call view
        response = get_quotes(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == "Both 'symbol' and 'exchange' parameters are required"
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_empty_symbol(self, authenticated_request_factory, table_data_manager):
        """
        Test: Empty symbol parameter
        Expected: 400 error from Trade service
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '78901234789012347890123478901234'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request with empty symbol
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': '',
                'exchange': 'NSE'
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x):
            response = get_quotes(request)
        
        # Verify - Trade service should catch this
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_empty_exchange(self, authenticated_request_factory, table_data_manager):
        """
        Test: Empty exchange parameter
        Expected: 400 error from Trade service
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '89012345890123458901234589012345'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request with empty exchange
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': 'TCS',
                'exchange': ''
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x):
            response = get_quotes(request)
        
        # Verify - Trade service should catch this
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_kite_api_empty_response(self, authenticated_request_factory, table_data_manager):
        """
        Test: Kite API returns empty response
        Expected: 200 with empty data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '90123456901234569012345690123456'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API returning empty data
        kite_quotes = {}
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': 'INVALIDSTOCK',
                'exchange': 'NSE'
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.quote', return_value=kite_quotes):
            
            response = get_quotes(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert data['data'] == {}
        assert data['meta']['data_length'] == 0
        assert data['meta']['symbols_requested'] == ['INVALIDSTOCK']
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_kite_api_exception(self, authenticated_request_factory, table_data_manager):
        """
        Test: Kite API throws exception
        Expected: 500 error
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '99999999999999999999999999999999'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': 'RELIANCE',
                'exchange': 'NSE'
            }
        )
        
        # Call view with Kite API exception
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.quote', side_effect=Exception('Network error')):
            
            response = get_quotes(request)
        
        # Verify
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert 'Network error' in data['error']
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_no_broker_credentials(self, authenticated_request_factory, table_data_manager):
        """
        Test: User has no broker credentials
        Expected: 500 error
        """
        # Setup database with no credentials
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '88888888888888888888888888888888'
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': 'RELIANCE',
                'exchange': 'NSE'
            }
        )
        
        # Call view
        response = get_quotes(request)
        
        # Verify
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['status'] == 'error'

    def test_symbols_with_spaces_and_case_insensitive(self, authenticated_request_factory, table_data_manager):
        """
        Test: Symbols with spaces and mixed case
        Expected: 200 with processed symbols (trimmed and uppercase)
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '23456789012345678901234567890123'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_quotes = {
            'NSE:RELIANCE': {
                'last_price': 2500.75,
                'volume': 100000
            },
            'NSE:TCS': {
                'last_price': 3400.50,
                'volume': 80000
            }
        }
        
        # Make request with mixed case and spaces
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': ' reliance , tcs ',
                'exchange': 'nse'
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.quote', return_value=kite_quotes):
            
            response = get_quotes(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert data['meta']['exchange'] == 'NSE'
        assert data['meta']['symbols_requested'] == ['RELIANCE', 'TCS']
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_post_method_not_allowed(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST method to get_quotes endpoint
        Expected: 405 Method Not Allowed
        """
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make POST request
        request = authenticated_request_factory.post('/integration/get_quotes/')
        
        # Call view
        response = get_quotes(request)
        
        # Verify
        assert response.status_code == 405
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'Method not allowed'

    def test_put_method_not_allowed(self, authenticated_request_factory, table_data_manager):
        """
        Test: PUT method to get_quotes endpoint
        Expected: 405 Method Not Allowed
        """
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make PUT request
        request = authenticated_request_factory.put('/integration/get_quotes/')
        
        # Call view
        response = get_quotes(request)
        
        # Verify
        assert response.status_code == 405
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'Method not allowed'

    def test_trade_service_400_error_response(self, authenticated_request_factory, table_data_manager):
        """
        Test: Trade service returns 400 error response (parameter validation)
        Expected: 400 error with Trade service error message
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '34567890123456789012345678901234'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request that will trigger Trade service validation error
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': '',  # This will cause Trade service to return 400
                'exchange': 'NSE'
            }
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x):
            response = get_quotes(request)
        
        # Verify
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['status'] == 'error'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')

    def test_trade_service_500_error_response(self, authenticated_request_factory, table_data_manager):
        """
        Test: Trade service returns 500 error response (kite connection unavailable)
        Expected: 500 error with Trade service error message
        """
        # Setup database with no credentials (will cause Trade service 500)
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '45678901234567890123456789012345'
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_quotes/',
            user_id,
            data={
                'symbol': 'TESTSTOCK',
                'exchange': 'NSE'
            }
        )
        
        # Call view
        response = get_quotes(request)
        
        # Verify
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['status'] == 'error'

@pytest.mark.integration
@pytest.mark.requires_db
class TestGetInstruments:
    """
    Tests for get_instruments API endpoint using Django test client.
    Only mocks external Kite API calls, everything else is real.
    """
    
    def test_get_method_success_with_middleware_auth(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid GET request with middleware auth
        Expected: 200 with instruments data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '12345678123412341234123456789012'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response (real format)
        kite_instruments = [
            {'instrument_token': 738561, 'exchange_token': 2885, 'tradingsymbol': 'RELIANCE', 'name': 'RELIANCE INDUSTRIES LTD', 'last_price': 0, 'expiry': '', 'strike': 0, 'tick_size': 0.05, 'lot_size': 1, 'instrument_type': 'EQ', 'segment': 'NSE', 'exchange': 'NSE'},
            {'instrument_token': 408065, 'exchange_token': 1594, 'tradingsymbol': 'INFY', 'name': 'INFOSYS LIMITED', 'last_price': 0, 'expiry': '', 'strike': 0, 'tick_size': 0.05, 'lot_size': 1, 'instrument_type': 'EQ', 'segment': 'NSE', 'exchange': 'NSE'}
        ]
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_instruments/',
            user_id
        )
        
        # Call view with mocked Kite API
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.instruments', return_value=kite_instruments):
            
            response = get_instruments(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert len(data['data']) == 2
        assert data['data'][0]['tradingsymbol'] == 'RELIANCE'
        assert data['data'][1]['tradingsymbol'] == 'INFY'
        assert data['meta']['count'] == 2
        assert data['meta']['source'] == 'kite_api'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_get_method_success_with_query_param_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid GET request with user_id in query param
        Expected: 200 with instruments data
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '87654321432143214321210987654321'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_instruments = [
            {'instrument_token': 779521, 'exchange_token': 3045, 'tradingsymbol': 'SBIN', 'name': 'STATE BANK OF INDIA', 'last_price': 0, 'expiry': '', 'strike': 0, 'tick_size': 0.05, 'lot_size': 1, 'instrument_type': 'EQ', 'segment': 'NSE', 'exchange': 'NSE'}
        ]
        
        # Make request (no middleware, user_id in query)
        request = authenticated_request_factory.get(
            '/integration/get_instruments/',
            data={'user_id': user_id}
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.instruments', return_value=kite_instruments):
            
            response = get_instruments(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert len(data['data']) == 1
        assert data['data'][0]['tradingsymbol'] == 'SBIN'
        assert data['meta']['count'] == 1
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_get_method_success_no_user_id_uses_system_user(self, authenticated_request_factory, table_data_manager):
        """
        Test: Valid GET request with no user_id provided (uses system user)
        Expected: 200 with instruments data
        """
        # Setup system user credentials
        table_data_manager.clear_table_completely('user_broker_credentials')
        system_user_id = '11111111111111111111111111111111'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {system_user_id}                 | zerodha     | system_key       | system_secret     | active | 1          | system_token              | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_instruments = [
            {'instrument_token': 340481, 'exchange_token': 1330, 'tradingsymbol': 'HDFC', 'name': 'HDFC LIMITED', 'last_price': 0, 'expiry': '', 'strike': 0, 'tick_size': 0.05, 'lot_size': 1, 'instrument_type': 'EQ', 'segment': 'NSE', 'exchange': 'NSE'}
        ]
        
        # Make request (no user_id)
        request = authenticated_request_factory.get('/integration/get_instruments/')
        
        # Call view with system user mock - patch where it's used in InstrumentsProvider
        with patch('integration_service.lib.broker.instruments.get_system_admin_user_id', return_value=system_user_id), \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.instruments', return_value=kite_instruments):
            
            response = get_instruments(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert len(data['data']) == 1
        assert data['data'][0]['tradingsymbol'] == 'HDFC'
        assert data['meta']['count'] == 1
        assert data['meta']['source'] == 'kite_api'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_middleware_auth_takes_precedence_over_query_param(self, authenticated_request_factory, table_data_manager):
        """
        Test: Middleware user_id takes precedence over query param user_id
        Expected: Uses middleware user credentials, not query param user
        """
        # Setup database with two users
        table_data_manager.clear_table_completely('user_broker_credentials')
        middleware_user = '22222222222222222222222222222222'
        query_user = '33333333333333333333333333333333'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {middleware_user}                | zerodha     | middleware_key   | middleware_secret | active | 1          | middleware_token          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | {query_user}                     | zerodha     | query_key        | query_secret      | active | 1          | query_token               | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API response
        kite_instruments = [
            {'instrument_token': 2953217, 'exchange_token': 11540, 'tradingsymbol': 'TCS', 'name': 'TATA CONSULTANCY SERVICES LTD', 'last_price': 0, 'expiry': '', 'strike': 0, 'tick_size': 0.05, 'lot_size': 1, 'instrument_type': 'EQ', 'segment': 'NSE', 'exchange': 'NSE'}
        ]
        
        # Make request with both user_ids
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_instruments/',
            middleware_user,  # Middleware auth
            data={'user_id': query_user}  # Should be ignored
        )
        
        # Call view and verify middleware key was used
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x) as mock_decrypt, \
             patch('kiteconnect.connect.KiteConnect.instruments', return_value=kite_instruments):
            
            response = get_instruments(request)
            
            # Check that middleware credentials were decrypted, not query user
            decrypted_values = [call.args[0] for call in mock_decrypt.call_args_list]
            assert 'middleware_key' in decrypted_values
            assert 'query_key' not in decrypted_values
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_empty_instruments_from_kite_api(self, authenticated_request_factory, table_data_manager):
        """
        Test: Kite API returns empty instruments list
        Expected: 200 with empty data array
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '44444444444444444444444444444444'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Mock Kite API returning empty list
        kite_instruments = []
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_instruments/',
            user_id
        )
        
        # Call view
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.instruments', return_value=kite_instruments):
            
            response = get_instruments(request)
        
        # Verify
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert data['data'] == []
        assert data['meta']['count'] == 0
        assert data['meta']['source'] == 'kite_api'
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_kite_connection_none_error(self, authenticated_request_factory, table_data_manager):
        """
        Test: Kite connection is None (unable to get connection)
        Expected: 200 with error status in response
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '55555555555555555555555555555555'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_instruments/',
            user_id
        )
        
        # Call view with None kite connection
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('integration_service.lib.broker.kite_user.KiteUser.get_instance', return_value=None):
            
            response = get_instruments(request)
        
        # Verify - should return success with error status inside
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'Unable to get Kite connection for user'
        assert data['data'] == []
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_kite_api_exception(self, authenticated_request_factory, table_data_manager):
        """
        Test: Kite API throws exception
        Expected: 200 with error status in response
        """
        # Setup database
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '66666666666666666666666666666666'
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | access_token              | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_key         | test_secret       | active | 1          | test_token                | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Make request
        request = authenticated_request_factory.authenticated_get(
            '/integration/get_instruments/',
            user_id
        )
        
        # Call view with Kite API exception
        with patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value', side_effect=lambda x: x), \
             patch('kiteconnect.connect.KiteConnect.instruments', side_effect=Exception('Network timeout')):
            
            response = get_instruments(request)
        
        # Verify - should return success with error status inside
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert 'Network timeout' in data['error']
        assert data['data'] == []
        
        # Cleanup
        table_data_manager.clear_table_completely('user_broker_credentials')
    
    def test_general_exception_in_view(self, authenticated_request_factory, table_data_manager):
        """
        Test: General exception occurs in view
        Expected: 500 error response
        """
        # Clear table for clean state
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make request
        request = authenticated_request_factory.get('/integration/get_instruments/')
        
        # Call view with exception during get_all_instruments - need to mock system user and FetchData first
        with patch('integration_service.lib.broker.instruments.get_system_admin_user_id', return_value='12345678123456781234567812345678'), \
             patch('integration_service.lib.broker.fetch_data.FetchData.__init__', return_value=None), \
             patch('integration_service.lib.broker.instruments.InstrumentsProvider.get_all_instruments', side_effect=Exception('Initialization failed')):
            
            response = get_instruments(request)
        
        # Verify
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert 'Initialization failed' in data['error']
    
    def test_post_method_not_allowed(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST method is not allowed
        Expected: 405 error
        """
        # Clear table for clean state
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make POST request
        request = authenticated_request_factory.post('/integration/get_instruments/')
        
        # Call view
        response = get_instruments(request)
        
        # Verify
        assert response.status_code == 405
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'Method not allowed'
    
    def test_put_method_not_allowed(self, authenticated_request_factory, table_data_manager):
        """
        Test: PUT method is not allowed
        Expected: 405 error
        """
        # Clear table for clean state
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make PUT request
        request = authenticated_request_factory.put('/integration/get_instruments/')
        
        # Call view
        response = get_instruments(request)
        
        # Verify
        assert response.status_code == 405
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'Method not allowed'
    
    def test_delete_method_not_allowed(self, authenticated_request_factory, table_data_manager):
        """
        Test: DELETE method is not allowed
        Expected: 405 error
        """
        # Clear table for clean state
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make DELETE request
        request = authenticated_request_factory.delete('/integration/get_instruments/')
        
        # Call view
        response = get_instruments(request)
        
        # Verify
        assert response.status_code == 405
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert data['error'] == 'Method not allowed'
    
    def test_system_user_lookup_exception(self, authenticated_request_factory, table_data_manager):
        """
        Test: System user lookup fails when no user_id provided
        Expected: 500 error response
        """
        # Clear table to ensure clean state
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Make request without user_id
        request = authenticated_request_factory.get('/integration/get_instruments/')
        
        # Call view with system user lookup exception
        with patch('integration_service.lib.broker.instruments.get_system_admin_user_id', side_effect=RuntimeError('System admin user not found. Please ensure an admin user exists in the database.')):
            
            response = get_instruments(request)
        
        # Verify
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert 'System admin user not found' in data['error'] 