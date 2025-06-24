"""
Integration tests for broker_view.py

Simple input-output tests for broker view functions:
- Setup data needed for all tests
- Each test: setup specific data → input → process → output → compare
- No testing of test infrastructure itself
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from integration_service.views.broker_view import register_broker, get_user_brokers, set_default_broker
from integration_service.models.UserBrokerCredential import UserBrokerCredential


@pytest.mark.integration
@pytest.mark.requires_db
class TestRegisterBroker:
    """
    Tests for register_broker view using simple input-output pattern.
    """
    
    def test_register_broker_success_with_json_data(self, authenticated_request_factory, table_data_manager):
        """
        Test: User registers first broker with JSON data
        Input: POST request with valid JSON data (broker_name, api_key, api_secret)
        Expected Output: 201 response with credential data, is_default=True
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '12345678123412341234123456789012'  # 32 chars as stored in database
        
        # Input
        request_data = {
            'broker_name': 'zerodha',
            'api_key': 'test_api_key_12345',
            'api_secret': 'test_api_secret_67890'
        }
        request = authenticated_request_factory.authenticated_post('/broker/register', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'success'
        expected_broker_name = 'zerodha'
        expected_is_default = True
        expected_status_value = 'pending_verification'
        
        # Process
        with patch('integration_service.lib.broker.broker_service.BrokerService._encrypt_value') as mock_encrypt, \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value') as mock_decrypt:
            
            # Mock encryption to return input as-is (for test data)
            mock_encrypt.side_effect = lambda x: x  # Return input as-is (no encryption)
            mock_decrypt.side_effect = lambda x: x  # Return input as-is (no decryption)
            
            response = register_broker(request)
        
        # Compare output
        assert response.status_code == 201
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['data']['broker_name'] == expected_broker_name
        assert response_data['data']['is_default'] == expected_is_default
        assert response_data['data']['status'] == expected_status_value
        assert 'credential_id' in response_data['data']
    
    def test_register_broker_success_with_form_data(self, authenticated_request_factory, table_data_manager):
        """
        Test: User registers broker with form data instead of JSON
        Input: POST request with form data
        Expected Output: 201 response with credential data
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '87654321432143214321210987654321'  # 32 chars as stored in database
        
        # Input
        request_data = {
            'broker_name': 'zerodha',
            'api_key': 'test_form_api_key',
            'api_secret': 'test_form_api_secret'
        }
        request = authenticated_request_factory.authenticated_post('/broker/register', user_id, data=request_data)
        
        # Expected output
        expected_status = 'success'
        expected_broker_name = 'zerodha'
        expected_is_default = True
        
        # Process
        with patch('integration_service.lib.broker.broker_service.BrokerService._encrypt_value') as mock_encrypt, \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value') as mock_decrypt:
            
            mock_encrypt.side_effect = lambda x: x
            mock_decrypt.side_effect = lambda x: x
            
            response = register_broker(request)
        
        # Compare output
        assert response.status_code == 201
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['data']['broker_name'] == expected_broker_name
        assert response_data['data']['is_default'] == expected_is_default
    
    def test_register_broker_fails_without_auth_middleware(self, authenticated_request_factory, table_data_manager):
        """
        Test: User tries to register broker without proper authentication
        Input: POST request with user_id in JSON body (no auth middleware)
        Expected Output: 400 error response - should require proper authentication
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '11111111111111111111111111111111'  # 32 chars as stored in database
        
        # Input - no user_data in request, trying to pass user_id in body (security vulnerability)
        request_data = {
            'user_id': user_id,
            'broker_name': 'zerodha',
            'api_key': 'test_no_auth_api_key',
            'api_secret': 'test_no_auth_api_secret'
        }
        request = authenticated_request_factory.post('/broker/register')
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output - should fail without proper authentication
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = register_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_register_second_broker_not_default(self, authenticated_request_factory, table_data_manager):
        """
        Test: User registers second broker, should not be default
        Input: POST request when user already has one broker
        Expected Output: 201 response with is_default=False
        """
        # Setup test data - user already has one broker
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '22222222222222222222222222222222'  # 32 chars as stored in database
        
        existing_credentials = f"""
        +----------------------------------+-------------+------------------+-------------------+---------------------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status              | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+---------------------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | existing_api_key | existing_secret   | pending_verification| 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+---------------------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', existing_credentials)
        
        # Input
        request_data = {
            'broker_name': 'zerodha',
            'api_key': 'second_api_key_12345',
            'api_secret': 'second_api_secret_67890'
        }
        request = authenticated_request_factory.authenticated_post('/broker/register', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'success'
        expected_is_default = False
        
        # Process
        with patch('integration_service.lib.broker.broker_service.BrokerService._encrypt_value') as mock_encrypt, \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value') as mock_decrypt:
            
            mock_encrypt.side_effect = lambda x: x
            mock_decrypt.side_effect = lambda x: x
            
            response = register_broker(request)
        
        # Compare output
        assert response.status_code == 201
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['data']['is_default'] == expected_is_default
    
    def test_register_broker_wrong_http_method(self, authenticated_request_factory, table_data_manager):
        """
        Test: GET request instead of POST
        Input: GET request to register_broker
        Expected Output: 405 method not allowed
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '33333333333333333333333333333333'  # 32 chars as stored in database
        
        # Input
        request = authenticated_request_factory.authenticated_get('/broker/register', user_id)
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Method not allowed'
        
        # Process
        response = register_broker(request)
        
        # Compare output
        assert response.status_code == 405
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_register_broker_missing_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request without user_id
        Input: POST request without user_data or user_id in body
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Input - no user_data set on request
        request_data = {
            'broker_name': 'zerodha',
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret'
        }
        request = authenticated_request_factory.post('/broker/register')
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = register_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_register_broker_missing_broker_name(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request missing broker_name
        Input: POST request without broker_name field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '44444444444444444444444444444444'  # 32 chars as stored in database
        
        # Input
        request_data = {
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret'
        }
        request = authenticated_request_factory.authenticated_post('/broker/register', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Missing required field: broker_name'
        
        # Process
        response = register_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_register_broker_missing_api_key(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request missing api_key
        Input: POST request without api_key field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '55555555555555555555555555555555'  # 32 chars as stored in database
        
        # Input
        request_data = {
            'broker_name': 'zerodha',
            'api_secret': 'test_api_secret'
        }
        request = authenticated_request_factory.authenticated_post('/broker/register', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Missing required field: api_key'
        
        # Process
        response = register_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_register_broker_missing_api_secret(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request missing api_secret
        Input: POST request without api_secret field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '66666666666666666666666666666666'  # 32 chars as stored in database
        
        # Input
        request_data = {
            'broker_name': 'zerodha',
            'api_key': 'test_api_key'
        }
        request = authenticated_request_factory.authenticated_post('/broker/register', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Missing required field: api_secret'
        
        # Process
        response = register_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_register_broker_invalid_json(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request with malformed JSON
        Input: POST request with invalid JSON body
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '77777777777777777777777777777777'  # 32 chars as stored in database
        
        # Input
        request = authenticated_request_factory.authenticated_post('/broker/register', user_id)
        request._body = b'{"invalid": json malformed}'  # Invalid JSON
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Invalid JSON in request body'
        
        # Process
        response = register_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error


@pytest.mark.integration
@pytest.mark.requires_db
class TestGetUserBrokers:
    """
    Tests for get_user_brokers view using simple input-output pattern.
    """
    
    def test_get_user_brokers_single_broker(self, authenticated_request_factory, table_data_manager):
        """
        Test: User with single broker requests broker list
        Input: GET request from user with one broker
        Expected Output: 200 response with array containing one broker
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '12345678123412341234123456789012'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_api_key_123 | test_secret_456   | active | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Input
        request = authenticated_request_factory.authenticated_get('/broker/list', user_id)
        
        # Expected output
        expected_status = 'success'
        expected_count = 1
        expected_broker_name = 'zerodha'
        expected_is_default = True
        expected_status_value = 'active'
        
        # Process
        response = get_user_brokers(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['meta']['count'] == expected_count
        assert len(response_data['data']) == expected_count
        assert response_data['data'][0]['broker_name'] == expected_broker_name
        assert response_data['data'][0]['is_default'] == expected_is_default
        assert response_data['data'][0]['status'] == expected_status_value
        assert 'credential_id' in response_data['data'][0]
        assert 'created_at' in response_data['data'][0]
    
    def test_get_user_brokers_multiple_brokers(self, authenticated_request_factory, table_data_manager):
        """
        Test: User with multiple brokers requests broker list
        Input: GET request from user with 3 brokers (different statuses, one default)
        Expected Output: 200 response with all 3 brokers
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '87654321432143214321210987654321'  # 32 chars as stored in database
        
        multiple_credentials = f"""
        +----------------------------------+-------------+-------------+---------------+---------------------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key     | api_secret    | status              | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+-------------+---------------+---------------------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | key1        | secret1       | active              | 0          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | {user_id}                        | zerodha     | default_key | default_secret| active              | 1          | 2024-01-15 10:01:00 | 2024-01-15 10:01:00 |
        | {user_id}                        | zerodha     | key3        | secret3       | pending_verification| 0          | 2024-01-15 10:02:00 | 2024-01-15 10:02:00 |
        +----------------------------------+-------------+-------------+---------------+---------------------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', multiple_credentials)
        
        # Input
        request = authenticated_request_factory.authenticated_get('/broker/list', user_id)
        
        # Expected output
        expected_status = 'success'
        expected_count = 3
        
        # Process
        response = get_user_brokers(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['meta']['count'] == expected_count
        assert len(response_data['data']) == expected_count
        
        # Verify one broker is default
        default_brokers = [broker for broker in response_data['data'] if broker['is_default']]
        assert len(default_brokers) == 1
        assert default_brokers[0]['broker_name'] == 'zerodha'
    
    def test_get_user_brokers_no_brokers(self, authenticated_request_factory, table_data_manager):
        """
        Test: User with no brokers requests broker list
        Input: GET request from user with no brokers
        Expected Output: 200 response with empty data array
        """
        # Setup test data - clear table so no brokers exist
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '11111111111111111111111111111111'  # 32 chars as stored in database
        
        # Input
        request = authenticated_request_factory.authenticated_get('/broker/list', user_id)
        
        # Expected output
        expected_status = 'success'
        expected_count = 0
        
        # Process
        response = get_user_brokers(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['meta']['count'] == expected_count
        assert len(response_data['data']) == expected_count
        assert response_data['data'] == []
    
    def test_get_user_brokers_fails_without_auth_middleware(self, authenticated_request_factory, table_data_manager):
        """
        Test: User tries to get brokers without proper authentication
        Input: GET request with user_id in query params (no auth middleware)
        Expected Output: 400 error response - should require proper authentication
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '22222222222222222222222222222222'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_query_key   | test_query_secret | active | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Input - no user_data set on request, trying to pass user_id in query (security vulnerability)
        request = authenticated_request_factory.get(f'/broker/list?user_id={user_id}')
        
        # Expected output - should fail without proper authentication
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = get_user_brokers(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_get_user_brokers_wrong_http_method(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request instead of GET
        Input: POST request to get_user_brokers
        Expected Output: 405 method not allowed
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '33333333333333333333333333333333'  # 32 chars as stored in database
        
        # Input
        request = authenticated_request_factory.authenticated_post('/broker/list', user_id)
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Method not allowed'
        
        # Process
        response = get_user_brokers(request)
        
        # Compare output
        assert response.status_code == 405
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_get_user_brokers_missing_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: GET request without user_id
        Input: GET request without user_data or user_id in query params
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Input - no user_data set on request
        request = authenticated_request_factory.get('/broker/list')
        
        # Expected output
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = get_user_brokers(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error 


@pytest.mark.integration
@pytest.mark.requires_db
class TestSetDefaultBroker:
    """
    Tests for set_default_broker view using simple input-output pattern.
    """
    
    def test_set_default_broker_success_json(self, authenticated_request_factory, table_data_manager):
        """
        Test: User sets second broker as default with JSON data
        Input: POST request with credential_id of second broker
        Expected Output: 200 response, second broker now default
        """
        # Setup test data - user has 2 brokers, second is not default
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '12345678123412341234123456789012'  # 32 chars as stored in database
        
        multiple_credentials = f"""
        +----------------------------------+-------------+-------------+---------------+---------------------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key     | api_secret    | status              | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+-------------+---------------+---------------------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | first_key   | first_secret  | active              | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | {user_id}                        | zerodha     | second_key  | second_secret | active              | 0          | 2024-01-15 10:01:00 | 2024-01-15 10:01:00 |
        +----------------------------------+-------------+-------------+---------------+---------------------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', multiple_credentials)
        
        # Get the credential_id of the second broker
        second_credential = UserBrokerCredential.objects.filter(user_id=user_id, api_key='second_key').first()
        credential_id = second_credential.id
        
        # Input
        request_data = {
            'credential_id': credential_id
        }
        request = authenticated_request_factory.authenticated_post('/broker/set-default', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'success'
        expected_broker_name = 'zerodha'
        expected_is_default = True
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['data']['credential_id'] == credential_id
        assert response_data['data']['broker_name'] == expected_broker_name
        assert response_data['data']['is_default'] == expected_is_default
    
    def test_set_default_broker_success_form_data(self, authenticated_request_factory, table_data_manager):
        """
        Test: User sets broker as default with form data
        Input: POST request with form data instead of JSON
        Expected Output: 200 response with updated broker status
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '87654321432143214321210987654321'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_form_key    | test_form_secret  | active | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Get the credential_id
        credential = UserBrokerCredential.objects.filter(user_id=user_id).first()
        credential_id = credential.id
        
        # Input
        request_data = {
            'credential_id': credential_id
        }
        request = authenticated_request_factory.authenticated_post('/broker/set-default', user_id, data=request_data)
        
        # Expected output
        expected_status = 'success'
        expected_is_default = True
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['data']['is_default'] == expected_is_default
    
    def test_set_default_broker_already_default(self, authenticated_request_factory, table_data_manager):
        """
        Test: User sets broker that is already default
        Input: POST request to set already default broker as default
        Expected Output: 200 response (idempotent operation)
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '11111111111111111111111111111111'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | default_key      | default_secret    | active | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Get the credential_id
        credential = UserBrokerCredential.objects.filter(user_id=user_id).first()
        credential_id = credential.id
        
        # Input
        request_data = {
            'credential_id': credential_id
        }
        request = authenticated_request_factory.authenticated_post('/broker/set-default', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'success'
        expected_is_default = True
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['data']['is_default'] == expected_is_default
    
    def test_set_default_broker_wrong_http_method(self, authenticated_request_factory, table_data_manager):
        """
        Test: GET request instead of POST
        Input: GET request to set_default_broker
        Expected Output: 405 method not allowed
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '22222222222222222222222222222222'  # 32 chars as stored in database
        
        # Input
        request = authenticated_request_factory.authenticated_get('/broker/set-default', user_id)
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Method not allowed'
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 405
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_set_default_broker_missing_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request without user_id
        Input: POST request without user_data or user_id in body
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Input - no user_data set on request
        request_data = {
            'credential_id': 123
        }
        request = authenticated_request_factory.post('/broker/set-default')
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_set_default_broker_missing_credential_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request without credential_id
        Input: POST request without credential_id field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '33333333333333333333333333333333'  # 32 chars as stored in database
        
        # Input
        request_data = {}  # Missing credential_id
        request = authenticated_request_factory.authenticated_post('/broker/set-default', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Missing required field: credential_id'
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_set_default_broker_invalid_credential_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request with non-existent credential_id
        Input: POST request with credential_id that doesn't exist
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '44444444444444444444444444444444'  # 32 chars as stored in database
        
        # Input
        request_data = {
            'credential_id': 99999  # Non-existent credential_id
        }
        request = authenticated_request_factory.authenticated_post('/broker/set-default', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert 'error' in response_data
    
    def test_set_default_broker_wrong_user_credential(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request with credential_id belonging to different user
        Input: POST request with another user's credential_id
        Expected Output: 400 error response
        """
        # Setup test data - create credentials for two different users
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id_1 = '55555555555555555555555555555555'  # 32 chars as stored in database
        user_id_2 = '66666666666666666666666666666666'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | {user_id_1}                      | zerodha     | user1_key        | user1_secret      | active | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | {user_id_2}                      | zerodha     | user2_key        | user2_secret      | active | 1          | 2024-01-15 10:01:00 | 2024-01-15 10:01:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Get credential_id of user2's credential
        user2_credential = UserBrokerCredential.objects.filter(user_id=user_id_2).first()
        user2_credential_id = user2_credential.id
        
        # Input - user1 tries to set user2's credential as default
        request_data = {
            'credential_id': user2_credential_id
        }
        request = authenticated_request_factory.authenticated_post('/broker/set-default', user_id_1)
        request._body = json.dumps(request_data).encode('utf-8')
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert 'error' in response_data
    
    def test_set_default_broker_invalid_json(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request with malformed JSON
        Input: POST request with invalid JSON body
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '77777777777777777777777777777777'  # 32 chars as stored in database
        
        # Input
        request = authenticated_request_factory.authenticated_post('/broker/set-default', user_id)
        request._body = b'{"invalid": json malformed}'  # Invalid JSON
        request.content_type = 'application/json'
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Invalid JSON in request body'
        
        # Process
        response = set_default_broker(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error


@pytest.mark.integration
@pytest.mark.requires_db
class TestBrokerViewIntegration:
    """
    Integration tests covering full broker lifecycle scenarios.
    """
    
    def test_full_broker_lifecycle(self, authenticated_request_factory, table_data_manager):
        """
        Test: Complete broker lifecycle - register → get → register second → set default → get
        Input: Multiple API calls simulating real user workflow
        Expected Output: State consistency throughout the workflow
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '88888888888888888888888888888888'  # 32 chars as stored in database
        
        # Step 1: Register first broker
        request_data_1 = {
            'broker_name': 'zerodha',
            'api_key': 'first_broker_key',
            'api_secret': 'first_broker_secret'
        }
        request_1 = authenticated_request_factory.authenticated_post('/broker/register', user_id)
        request_1._body = json.dumps(request_data_1).encode('utf-8')
        request_1.content_type = 'application/json'
        
        # Process step 1
        with patch('integration_service.lib.broker.broker_service.BrokerService._encrypt_value') as mock_encrypt, \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value') as mock_decrypt:
            
            mock_encrypt.side_effect = lambda x: x
            mock_decrypt.side_effect = lambda x: x
            
            response_1 = register_broker(request_1)
        
        # Verify step 1
        assert response_1.status_code == 201
        response_data_1 = json.loads(response_1.content)
        assert response_data_1['data']['is_default'] == True
        first_credential_id = response_data_1['data']['credential_id']
        
        # Step 2: Get brokers (should show 1 broker)
        request_2 = authenticated_request_factory.authenticated_get('/broker/list', user_id)
        response_2 = get_user_brokers(request_2)
        
        # Verify step 2
        assert response_2.status_code == 200
        response_data_2 = json.loads(response_2.content)
        assert response_data_2['meta']['count'] == 1
        assert response_data_2['data'][0]['is_default'] == True
        
        # Step 3: Register second broker
        request_data_3 = {
            'broker_name': 'zerodha',
            'api_key': 'second_broker_key',
            'api_secret': 'second_broker_secret'
        }
        request_3 = authenticated_request_factory.authenticated_post('/broker/register', user_id)
        request_3._body = json.dumps(request_data_3).encode('utf-8')
        request_3.content_type = 'application/json'
        
        # Process step 3
        with patch('integration_service.lib.broker.broker_service.BrokerService._encrypt_value') as mock_encrypt, \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value') as mock_decrypt:
            
            mock_encrypt.side_effect = lambda x: x
            mock_decrypt.side_effect = lambda x: x
            
            response_3 = register_broker(request_3)
        
        # Verify step 3
        assert response_3.status_code == 201
        response_data_3 = json.loads(response_3.content)
        assert response_data_3['data']['is_default'] == False
        second_credential_id = response_data_3['data']['credential_id']
        
        # Step 4: Set second broker as default
        request_data_4 = {
            'credential_id': second_credential_id
        }
        request_4 = authenticated_request_factory.authenticated_post('/broker/set-default', user_id)
        request_4._body = json.dumps(request_data_4).encode('utf-8')
        request_4.content_type = 'application/json'
        
        response_4 = set_default_broker(request_4)
        
        # Verify step 4
        assert response_4.status_code == 200
        response_data_4 = json.loads(response_4.content)
        assert response_data_4['data']['is_default'] == True
        
        # Step 5: Get brokers again (should show 2 brokers, second one default)
        request_5 = authenticated_request_factory.authenticated_get('/broker/list', user_id)
        response_5 = get_user_brokers(request_5)
        
        # Verify step 5
        assert response_5.status_code == 200
        response_data_5 = json.loads(response_5.content)
        assert response_data_5['meta']['count'] == 2
        
        # Verify only one broker is default and it's the second one
        default_brokers = [broker for broker in response_data_5['data'] if broker['is_default']]
        assert len(default_brokers) == 1
        assert default_brokers[0]['credential_id'] == second_credential_id
    
    def test_user_isolation(self, authenticated_request_factory, table_data_manager):
        """
        Test: Two different users with brokers should not see each other's data
        Input: Two users each with their own brokers
        Expected Output: Each user only sees/modifies their own brokers
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id_1 = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'  # 32 chars as stored in database
        user_id_2 = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | {user_id_1}                      | zerodha     | user1_key        | user1_secret      | active | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | {user_id_2}                      | zerodha     | user2_key        | user2_secret      | active | 1          | 2024-01-15 10:01:00 | 2024-01-15 10:01:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Test user 1 can only see their broker
        request_1 = authenticated_request_factory.authenticated_get('/broker/list', user_id_1)
        response_1 = get_user_brokers(request_1)
        
        assert response_1.status_code == 200
        response_data_1 = json.loads(response_1.content)
        assert response_data_1['meta']['count'] == 1
        assert response_data_1['data'][0]['credential_id'] == UserBrokerCredential.objects.filter(user_id=user_id_1).first().id
        
        # Test user 2 can only see their broker
        request_2 = authenticated_request_factory.authenticated_get('/broker/list', user_id_2)
        response_2 = get_user_brokers(request_2)
        
        assert response_2.status_code == 200
        response_data_2 = json.loads(response_2.content)
        assert response_data_2['meta']['count'] == 1
        assert response_data_2['data'][0]['credential_id'] == UserBrokerCredential.objects.filter(user_id=user_id_2).first().id
        
        # Verify user 1 cannot modify user 2's broker
        user2_credential_id = UserBrokerCredential.objects.filter(user_id=user_id_2).first().id
        request_data = {
            'credential_id': user2_credential_id
        }
        request_cross = authenticated_request_factory.authenticated_post('/broker/set-default', user_id_1)
        request_cross._body = json.dumps(request_data).encode('utf-8')
        request_cross.content_type = 'application/json'
        
        response_cross = set_default_broker(request_cross)
        
        # Should fail with error
        assert response_cross.status_code == 400
        response_data_cross = json.loads(response_cross.content)
        assert response_data_cross['status'] == 'error' 