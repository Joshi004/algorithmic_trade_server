"""
Integration tests for kite_auth_view.py

Simple input-output tests for get_login_url view:
- Setup data needed for all tests
- Each test: setup specific data → input → process → output → compare
- No testing of test infrastructure itself
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from integration_service.views.kite_auth_view import get_login_url, set_session, get_profile_info
from integration_service.models.UserBrokerCredential import UserBrokerCredential


@pytest.mark.integration
@pytest.mark.requires_db
class TestGetLoginUrl:
    """
    Tests for get_login_url view using simple input-output pattern.
    """
    
    def test_get_login_url_with_active_credentials(self, authenticated_request_factory, table_data_manager):
        """
        Test: User with active credentials requests login URL
        Input: GET request from user with active credentials
        Expected Output: 200 response with login URL
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '12345678123412341234123456789012'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_active_key  | test_active_secret| active | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Input
        request = authenticated_request_factory.authenticated_get('/kite/login-url', user_id)
        
        # Expected output
        expected_login_url = 'https://kite.trade/connect/login?api_key=test_active_key&v=3'
        
        # Process
        with patch('integration_service.lib.broker.kite_user.KiteConnect') as mock_kite_connect, \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value') as mock_decrypt:
            
            # Mock decryption to return plain text values (for test data)
            mock_decrypt.side_effect = lambda x: x  # Return input as-is (no decryption)
            
            mock_kite_instance = MagicMock()
            mock_kite_connect.return_value = mock_kite_instance
            mock_kite_instance.login_url.return_value = expected_login_url
            
            response = get_login_url(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content) 
        assert response_data['login_url'] == expected_login_url
    
    def test_get_login_url_with_pending_credentials(self, authenticated_request_factory, table_data_manager):
        """
        Test: User with pending credentials requests login URL
        Input: GET request from user with pending credentials  
        Expected Output: 200 response with login URL
        """
        # Setup test data
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '87654321432143214321210987654321'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+---------------------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status              | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+---------------------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_pending_key | test_pending_secret| pending_verification| 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+---------------------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Input
        request = authenticated_request_factory.authenticated_get('/kite/login-url', user_id)
        
        # Expected output
        expected_login_url = 'https://kite.trade/connect/login?api_key=test_pending_key&v=3'
        
        # Process
        with patch('integration_service.lib.broker.kite_user.KiteConnect') as mock_kite_connect, \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value') as mock_decrypt:
            
            # Mock decryption to return plain text values (for test data)
            mock_decrypt.side_effect = lambda x: x  # Return input as-is (no decryption)
            
            mock_kite_instance = MagicMock()
            mock_kite_connect.return_value = mock_kite_instance
            mock_kite_instance.login_url.return_value = expected_login_url
            
            response = get_login_url(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['login_url'] == expected_login_url
    
    def test_get_login_url_no_credentials(self, authenticated_request_factory, table_data_manager):
        """
        Test: User with no credentials requests login URL
        Input: GET request from user with no credentials
        Expected Output: 400 error response
        """
        # Setup test data - clear table so no credentials exist
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '11111111111111111111111111111111'  # 32 chars as stored in database
        
        # Input
        request = authenticated_request_factory.authenticated_get('/kite/login-url', user_id)
        
        # Expected output
        expected_status = 'error'
        expected_error = 'No broker credentials found'
        expected_error_code = 'NO_BROKER_CREDENTIALS'
        expected_message = 'Please register your broker credentials first'
        expected_redirect = 'broker_registration'
        
        # Process
        response = get_login_url(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
        assert response_data['error_code'] == expected_error_code
        assert response_data['message'] == expected_message
        assert response_data['redirect_to'] == expected_redirect
    
    def test_get_login_url_missing_user_id(self, authenticated_request_factory, table_data_manager):
        """
        Test: Request without user ID
        Input: GET request without user_data
        Expected Output: 400 error response
        """
        # Setup test data - clear table (no specific data needed for this test)
        table_data_manager.clear_table_completely('user_broker_credentials')
        
        # Input
        request = authenticated_request_factory.get('/kite/login-url')
        # No user_data set on request
        
        # Expected output
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = get_login_url(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_get_login_url_wrong_http_method(self, authenticated_request_factory, table_data_manager):
        """
        Test: POST request instead of GET
        Input: POST request to get_login_url
        Expected Output: 405 method not allowed
        """
        # Setup test data - need some credentials for the user
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = '12345678123412341234123456789012'  # 32 chars as stored in database
        
        credentials_data = f"""
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key          | api_secret        | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        | {user_id}                        | zerodha     | test_active_key  | test_active_secret| active | 1          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +----------------------------------+-------------+------------------+-------------------+--------+------------+---------------------+---------------------+
        """
        
        table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
        
        # Input
        request = authenticated_request_factory.authenticated_post('/kite/login-url', user_id)
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Method not allowed'
        
        # Process
        response = get_login_url(request)
        
        # Compare output
        assert response.status_code == 405
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_get_login_url_with_multiple_credentials_uses_default(self, authenticated_request_factory, table_data_manager):
        """
        Test: User with multiple credentials, only one default
        Input: User has 3 credentials, only one is_default=True
        Expected Output: Uses the default credential's API key
        """
        # Setup test data - clear table first
        table_data_manager.clear_table_completely('user_broker_credentials')
        test_user_id = '33333333333333333333333333333333'  # 32 chars as stored in database
        
        # Multiple credentials data - clearly visible in ASCII format
        multiple_credentials = f"""
        +----------------------------------+-------------+-------------+---------------+--------+------------+---------------------+---------------------+
        | user_id                          | broker_name | api_key     | api_secret    | status | is_default | created_at          | updated_at          |
        +----------------------------------+-------------+-------------+---------------+--------+------------+---------------------+---------------------+
        | {test_user_id}                   | zerodha     | key1        | secret1       | active | 0          | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | {test_user_id}                   | zerodha     | default_key | default_secret| active | 1          | 2024-01-15 10:01:00 | 2024-01-15 10:01:00 |
        | {test_user_id}                   | zerodha     | key3        | secret3       | active | 0          | 2024-01-15 10:02:00 | 2024-01-15 10:02:00 |
        +----------------------------------+-------------+-------------+---------------+--------+------------+---------------------+---------------------+
        """
        
        # Add the test data
        table_data_manager.insert_table_data('user_broker_credentials', multiple_credentials)
        
        # Input
        request = authenticated_request_factory.authenticated_get('/kite/login-url', test_user_id)
        
        # Expected output
        expected_login_url = 'https://kite.trade/connect/login?api_key=default_key&v=3'
        
        # Process
        with patch('integration_service.lib.broker.kite_user.KiteConnect') as mock_kite_connect, \
             patch('integration_service.lib.broker.broker_service.BrokerService._decrypt_value') as mock_decrypt:
            
            # Mock decryption to return plain text values (for test data)
            mock_decrypt.side_effect = lambda x: x  # Return input as-is (no decryption)
            
            mock_kite_instance = MagicMock()
            mock_kite_connect.return_value = mock_kite_instance
            mock_kite_instance.login_url.return_value = expected_login_url
            
            response = get_login_url(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['login_url'] == expected_login_url
        # Verify the correct API key was used
        mock_kite_connect.assert_called_once_with(api_key='default_key') 


@pytest.mark.integration
@pytest.mark.requires_db
class TestSetSession:
    """
    Tests for set_session view using simple input-output pattern.
    """
    
    def test_set_session_wrong_http_method(self, authenticated_request_factory):
        """
        Test: GET request instead of POST
        Input: GET request to set_session
        Expected Output: 405 method not allowed
        """
        # Input
        request = authenticated_request_factory.get('/kite/set-session')
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Method not allowed'
        
        # Process
        response = set_session(request)
        
        # Compare output
        assert response.status_code == 405
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_set_session_missing_request_token(self, authenticated_request_factory):
        """
        Test: POST request without request_token
        Input: POST request with JSON body missing request_token field
        Expected Output: 400 error response
        """
        # Input
        user_id = '12345678123412341234123456789012'
        request_data = {'user_id': user_id}  # Missing request_token
        request = authenticated_request_factory.authenticated_post('/kite/set-session', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Request token is required'
        
        # Process
        response = set_session(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_set_session_empty_request_token(self, authenticated_request_factory):
        """
        Test: POST request with empty request_token
        Input: POST request with empty string request_token
        Expected Output: 400 error response
        """
        # Input
        user_id = '12345678123412341234123456789012'
        request_data = {'request_token': '', 'user_id': user_id}
        request = authenticated_request_factory.authenticated_post('/kite/set-session', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Request token is required'
        
        # Process
        response = set_session(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_set_session_missing_user_id(self, authenticated_request_factory):
        """
        Test: POST request without user_id
        Input: POST request with request_token but no user_id in auth middleware or JSON body
        Expected Output: 400 error response
        """
        # Input - no user_data set on request
        request_data = {'request_token': 'valid_token'}
        request = authenticated_request_factory.post('/kite/set-session')
        request._body = json.dumps(request_data).encode('utf-8')
        
        # Expected output
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = set_session(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_set_session_success_with_user_data(self, authenticated_request_factory):
        """
        Test: Successful session setting with user_id from auth middleware
        Input: POST request with valid request_token and user_id from request.user_data
        Expected Output: 200 response with KiteUser success response
        """
        # Input
        user_id = '12345678123412341234123456789012'
        request_data = {'request_token': 'valid_token_123'}
        request = authenticated_request_factory.authenticated_post('/kite/set-session', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        
        # Expected output
        expected_response = {'status': 'success', 'access_token': 'access_token_123'}
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.set_session.return_value = expected_response
            
            response = set_session(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data == expected_response
        mock_kite_user.assert_called_once_with(user_id)
        mock_instance.set_session.assert_called_once_with('valid_token_123')
    
    def test_set_session_success_with_json_user_id(self, authenticated_request_factory):
        """
        Test: Successful session setting with user_id from JSON body
        Input: POST request with valid request_token and user_id in JSON body (no auth middleware)
        Expected Output: 200 response with KiteUser success response
        """
        # Input - no user_data in request
        user_id = '87654321432143214321210987654321'
        request_data = {'request_token': 'valid_token_456', 'user_id': user_id}
        request = authenticated_request_factory.post('/kite/set-session')
        request._body = json.dumps(request_data).encode('utf-8')
        
        # Expected output
        expected_response = {'status': 'success', 'access_token': 'access_token_456'}
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.set_session.return_value = expected_response
            
            response = set_session(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data == expected_response
        mock_kite_user.assert_called_once_with(user_id)
        mock_instance.set_session.assert_called_once_with('valid_token_456')
    
    def test_set_session_invalid_json(self, authenticated_request_factory):
        """
        Test: POST request with malformed JSON
        Input: POST request with invalid JSON body
        Expected Output: 500 error response with JSON decode error
        """
        # Input
        request = authenticated_request_factory.post('/kite/set-session')
        request._body = b'{"invalid": json malformed}'  # Invalid JSON
        
        # Expected output (error message will contain JSON decode details)
        expected_status_code = 500
        
        # Process
        response = set_session(request)
        
        # Compare output
        assert response.status_code == expected_status_code
        response_data = json.loads(response.content)
        assert response_data['status'] == 'error'
        assert 'error' in response_data
    
    def test_set_session_kite_user_exception(self, authenticated_request_factory):
        """
        Test: KiteUser raises exception
        Input: POST request with valid data but KiteUser.set_session raises exception
        Expected Output: 500 error response with exception message
        """
        # Input
        user_id = '12345678123412341234123456789012'
        request_data = {'request_token': 'valid_token_789'}
        request = authenticated_request_factory.authenticated_post('/kite/set-session', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        
        # Expected output
        expected_error_message = 'KiteUser connection failed'
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.set_session.side_effect = Exception(expected_error_message)
            
            response = set_session(request)
        
        # Compare output
        assert response.status_code == 500
        response_data = json.loads(response.content)
        assert response_data['status'] == 'error'
        assert response_data['error'] == expected_error_message
    
    def test_set_session_user_data_priority_over_json(self, authenticated_request_factory):
        """
        Test: user_data.public_id takes priority over JSON body user_id
        Input: POST request with user_id in both auth middleware and JSON body (different values)
        Expected Output: Should use user_id from request.user_data
        """
        # Input
        auth_user_id = '11111111111111111111111111111111'
        json_user_id = '22222222222222222222222222222222'
        request_data = {'request_token': 'valid_token_priority', 'user_id': json_user_id}
        request = authenticated_request_factory.authenticated_post('/kite/set-session', auth_user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        
        # Expected output
        expected_response = {'status': 'success', 'access_token': 'access_token_priority'}
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.set_session.return_value = expected_response
            
            response = set_session(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data == expected_response
        # Verify it used auth_user_id, not json_user_id
        mock_kite_user.assert_called_once_with(auth_user_id)
        mock_instance.set_session.assert_called_once_with('valid_token_priority')
    
    def test_set_session_kite_user_error_response(self, authenticated_request_factory):
        """
        Test: KiteUser returns error response (not exception)
        Input: POST request with valid data but KiteUser.set_session returns error response
        Expected Output: 200 response with KiteUser error response
        """
        # Input
        user_id = '12345678123412341234123456789012'
        request_data = {'request_token': 'invalid_token'}
        request = authenticated_request_factory.authenticated_post('/kite/set-session', user_id)
        request._body = json.dumps(request_data).encode('utf-8')
        
        # Expected output - KiteUser returns error response
        expected_response = {'status': 'error', 'error': 'Invalid request token'}
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.set_session.return_value = expected_response
            
            response = set_session(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data == expected_response
        mock_kite_user.assert_called_once_with(user_id)
        mock_instance.set_session.assert_called_once_with('invalid_token')


@pytest.mark.integration
@pytest.mark.requires_db
class TestGetProfileInfo:
    """
    Tests for get_profile_info view using simple input-output pattern.
    """
    
    def test_get_profile_info_wrong_http_method(self, authenticated_request_factory):
        """
        Test: POST request instead of GET
        Input: POST request to get_profile_info
        Expected Output: 405 method not allowed
        """
        # Input
        request = authenticated_request_factory.post('/kite/profile-info')
        
        # Expected output
        expected_status = 'error'
        expected_error = 'Method not allowed'
        
        # Process
        response = get_profile_info(request)
        
        # Compare output
        assert response.status_code == 405
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_get_profile_info_missing_user_data(self, authenticated_request_factory):
        """
        Test: GET request without user_data
        Input: GET request without request.user_data set
        Expected Output: 400 error response
        """
        # Input - no user_data set on request
        request = authenticated_request_factory.get('/kite/profile-info')
        
        # Expected output
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = get_profile_info(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_get_profile_info_empty_user_id_in_user_data(self, authenticated_request_factory):
        """
        Test: GET request with empty user_id in user_data
        Input: GET request with user_data containing empty public_id
        Expected Output: 400 error response
        """
        # Input
        request = authenticated_request_factory.get('/kite/profile-info')
        request.user_data = {'public_id': ''}  # Empty user_id
        
        # Expected output
        expected_status = 'error'
        expected_error = 'User ID is required'
        
        # Process
        response = get_profile_info(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == expected_error
    
    def test_get_profile_info_successful_retrieval(self, authenticated_request_factory):
        """
        Test: Successful profile retrieval
        Input: GET request with valid user_id from auth middleware
        Expected Output: 200 response with profile data
        """
        # Input
        user_id = '12345678123412341234123456789012'
        request = authenticated_request_factory.authenticated_get('/kite/profile-info', user_id)
        
        # Expected output
        expected_profile_data = {
            'user_id': 'ZX1234',
            'user_name': 'John Doe',
            'email': 'john@example.com',
            'broker': 'ZERODHA'
        }
        expected_response = {
            'status': 'success',
            'data': expected_profile_data
        }
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.get_profile_info.return_value = expected_profile_data
            
            response = get_profile_info(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data == expected_response
        mock_kite_user.assert_called_once_with(user_id)
        mock_instance.get_profile_info.assert_called_once()
    
    def test_get_profile_info_kite_user_error_response(self, authenticated_request_factory):
        """
        Test: KiteUser returns error response
        Input: GET request with valid user_id but KiteUser returns error dict
        Expected Output: 400 response with KITE_NOT_CONNECTED error format
        """
        # Input
        user_id = '87654321432143214321210987654321'
        request = authenticated_request_factory.authenticated_get('/kite/profile-info', user_id)
        
        # Expected output
        expected_status = 'error'
        expected_error_code = 'KITE_NOT_CONNECTED'
        expected_message = 'Please connect to Zerodha first'
        expected_action_required = 'connect_to_zerodha'
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.get_profile_info.return_value = {'error': 'Session not valid'}
            
            response = get_profile_info(request)
        
        # Compare output
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['status'] == expected_status
        assert response_data['error'] == 'Session not valid'
        assert response_data['error_code'] == expected_error_code
        assert response_data['message'] == expected_message
        assert response_data['action_required'] == expected_action_required
    
    def test_get_profile_info_kite_user_exception(self, authenticated_request_factory):
        """
        Test: KiteUser.get_profile_info raises exception
        Input: GET request with valid user_id but KiteUser method raises exception
        Expected Output: 500 error response with exception message
        """
        # Input
        user_id = '11111111111111111111111111111111'
        request = authenticated_request_factory.authenticated_get('/kite/profile-info', user_id)
        
        # Expected output
        expected_error_message = 'Network connection failed'
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.get_profile_info.side_effect = Exception(expected_error_message)
            
            response = get_profile_info(request)
        
        # Compare output
        assert response.status_code == 500
        response_data = json.loads(response.content)
        assert response_data['status'] == 'error'
        assert response_data['error'] == expected_error_message
    
    def test_get_profile_info_kite_user_constructor_exception(self, authenticated_request_factory):
        """
        Test: KiteUser constructor raises exception
        Input: GET request with valid user_id but KiteUser constructor raises exception
        Expected Output: 500 error response with exception message
        """
        # Input
        user_id = '22222222222222222222222222222222'
        request = authenticated_request_factory.authenticated_get('/kite/profile-info', user_id)
        
        # Expected output
        expected_error_message = 'Failed to initialize KiteUser'
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_kite_user.side_effect = Exception(expected_error_message)
            
            response = get_profile_info(request)
        
        # Compare output
        assert response.status_code == 500
        response_data = json.loads(response.content)
        assert response_data['status'] == 'error'
        assert response_data['error'] == expected_error_message
    
    def test_get_profile_info_non_dict_response(self, authenticated_request_factory):
        """
        Test: KiteUser returns non-dict response
        Input: GET request with valid user_id and KiteUser returns string/list response
        Expected Output: 200 success response with non-dict data
        """
        # Input
        user_id = '33333333333333333333333333333333'
        request = authenticated_request_factory.authenticated_get('/kite/profile-info', user_id)
        
        # Expected output
        expected_profile_data = 'Profile data as string'
        expected_response = {
            'status': 'success',
            'data': expected_profile_data
        }
        
        # Process
        with patch('integration_service.views.kite_auth_view.KiteUser') as mock_kite_user:
            mock_instance = MagicMock()
            mock_kite_user.return_value = mock_instance
            mock_instance.get_profile_info.return_value = expected_profile_data
            
            response = get_profile_info(request)
        
        # Compare output
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data == expected_response
        mock_kite_user.assert_called_once_with(user_id)
        mock_instance.get_profile_info.assert_called_once() 