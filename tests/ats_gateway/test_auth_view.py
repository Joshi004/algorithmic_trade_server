import pytest
import json
from django.test import Client
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from ats_gateway.views.AuthView import register, login, refresh_token, get_websocket_token, logout

User = get_user_model()


@pytest.mark.integration
@pytest.mark.requires_db
class TestRegister:



    def test_register_success_with_valid_complete_data(self, table_data_manager):
        """
        Test: Successful registration with all valid fields
        Input: POST request with valid email, password, first_name, last_name
        Expected Output: 201 response with user data
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'complete@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        
        # Expected output
        expected_status = 201
        expected_email = 'complete@example.com'
        expected_first_name = 'John'
        expected_last_name = 'Doe'
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['email'] == expected_email
        assert response_data['first_name'] == expected_first_name
        assert response_data['last_name'] == expected_last_name
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_register_success_with_minimal_data(self, table_data_manager):
        """
        Test: Successful registration with only required fields
        Input: POST request with email, password, first_name only
        Expected Output: 201 response with user data
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'minimal@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Jane'
        }
        
        # Expected output
        expected_status = 201
        expected_email = 'minimal@example.com'
        expected_first_name = 'Jane'
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['email'] == expected_email
        assert response_data['first_name'] == expected_first_name
        
        # Cleanup
        table_data_manager.clear_table_completely('users')



    def test_register_success_excludes_sensitive_data(self, table_data_manager):
        """
        Test: Successful registration excludes password from response
        Input: POST request with valid registration data including password
        Expected Output: Response does not contain password field
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'secure@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Charlie'
        }
        
        # Expected output
        expected_status = 201
        excluded_field = 'password'
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert excluded_field not in response_data
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_register_missing_email_field(self, table_data_manager):
        """
        Test: Registration fails when email is missing
        Input: POST request without email field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'password': 'ValidPassword123!',
            'first_name': 'John'
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'email' in response_data

    def test_register_missing_password_field(self, table_data_manager):
        """
        Test: Registration fails when password is missing
        Input: POST request without password field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'test@example.com',
            'first_name': 'John'
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'password' in response_data

    def test_register_missing_first_name_field(self, table_data_manager):
        """
        Test: Registration fails when first_name is missing
        Input: POST request without first_name field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'test@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'first_name' in response_data

    def test_register_invalid_email_format(self, table_data_manager):
        """
        Test: Registration fails with invalid email format
        Input: POST request with malformed email
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'invalid-email-format',
            'password': 'ValidPassword123!',
            'first_name': 'John'
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'email' in response_data

    def test_register_weak_password(self, table_data_manager):
        """
        Test: Registration fails with weak password
        Input: POST request with weak password
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'test@example.com',
            'password': '123',
            'first_name': 'John'
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'password' in response_data

    def test_register_empty_first_name(self, table_data_manager):
        """
        Test: Registration fails with empty first_name
        Input: POST request with empty string first_name
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'test@example.com',
            'password': 'ValidPassword123!',
            'first_name': ''
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'first_name' in response_data

    def test_register_whitespace_only_first_name(self, table_data_manager):
        """
        Test: Registration fails with whitespace-only first_name
        Input: POST request with whitespace-only first_name
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'test@example.com',
            'password': 'ValidPassword123!',
            'first_name': '   '
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'first_name' in response_data

    def test_register_duplicate_email(self, table_data_manager):
        """
        Test: Registration fails with duplicate email and preserves original user
        Input: POST request with email that already exists
        Expected Output: 400 error response, only one user in database, original user unchanged
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        duplicate_email = 'duplicate@example.com'
        
        # Create existing user first
        first_request_data = {
            'email': duplicate_email,
            'password': 'ValidPassword123!',
            'first_name': 'First'
        }
        first_response = client.post('/register/', first_request_data)
        assert first_response.status_code == 201
        
        # Try to register with same email
        second_request_data = {
            'email': duplicate_email,
            'password': 'ValidPassword456!',
            'first_name': 'Second'
        }
        
        # Expected output  
        expected_status = 400
        expected_user_count = 1
        expected_first_name = 'First'
        
        # Process
        response = client.post('/register/', second_request_data)
        
        # Compare output
        assert response.status_code == expected_status
        
        # Verify only one user exists with this email
        users_with_email = User.objects.filter(email=duplicate_email)
        assert users_with_email.count() == expected_user_count
        
        # Verify original user data is unchanged
        original_user = users_with_email.first()
        assert original_user.first_name == expected_first_name
        assert original_user.email == duplicate_email
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_register_duplicate_email_case_insensitive(self, table_data_manager):
        """
        Test: Registration fails with duplicate email in different case
        Input: POST request with email that exists but in different case
        Expected Output: 400 error response, case-insensitive email validation
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        original_email = 'CaseTest@example.com'
        duplicate_email_different_case = 'casetest@example.com'
        
        # Create existing user first
        first_request_data = {
            'email': original_email,
            'password': 'ValidPassword123!',
            'first_name': 'Original'
        }
        first_response = client.post('/register/', first_request_data)
        assert first_response.status_code == 201
        
        # Try to register with same email in different case
        second_request_data = {
            'email': duplicate_email_different_case,
            'password': 'ValidPassword456!',
            'first_name': 'Duplicate'
        }
        
        # Expected output
        expected_status = 400
        expected_user_count = 1
        
        # Process
        response = client.post('/register/', second_request_data)
        
        # Compare output
        assert response.status_code == expected_status
        
        # Verify only one user exists (case-insensitive check)
        users_count = User.objects.filter(email__iexact=original_email).count()
        assert users_count == expected_user_count
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_register_empty_request_body(self, table_data_manager):
        """
        Test: Registration fails with empty request body
        Input: POST request with no data
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {}
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status



    def test_register_whitespace_trimming_first_name(self, table_data_manager):
        """
        Test: Registration trims whitespace from first_name
        Input: POST request with first_name having leading/trailing whitespace
        Expected Output: 201 response with trimmed first_name
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'trim@example.com',
            'password': 'ValidPassword123!',
            'first_name': '  John  '
        }
        
        # Expected output
        expected_status = 201
        expected_first_name = 'John'
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['first_name'] == expected_first_name
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_register_whitespace_trimming_last_name(self, table_data_manager):
        """
        Test: Registration trims whitespace from last_name
        Input: POST request with last_name having leading/trailing whitespace
        Expected Output: 201 response with trimmed last_name
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'trimlast@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Jane',
            'last_name': '  Doe  '
        }
        
        # Expected output
        expected_status = 201
        expected_last_name = 'Doe'
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['last_name'] == expected_last_name
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_register_extra_fields_ignored(self, table_data_manager):
        """
        Test: Registration ignores extra unexpected fields
        Input: POST request with additional fields not in serializer
        Expected Output: 201 response ignoring extra fields
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'email': 'extra@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Extra',
            'last_name': 'Fields',
            'unexpected_field': 'should_be_ignored',
            'another_field': 'also_ignored'
        }
        
        # Expected output
        expected_status = 201
        expected_email = 'extra@example.com'
        
        # Process
        response = client.post('/register/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['email'] == expected_email
        assert 'unexpected_field' not in response_data
        assert 'another_field' not in response_data
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

 


@pytest.mark.integration
@pytest.mark.requires_db
class TestLogin:



    def test_login_success_with_valid_credentials(self, table_data_manager):
        """
        Test: Successful login with valid email and password
        Input: POST request with correct email and password
        Expected Output: 200 response with user data and token info
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'validlogin@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Valid',
            'last_name': 'User'
        }
        client.post('/register/', user_data)
        
        login_data = {
            'email': 'validlogin@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 200
        expected_message = 'Login successful'
        expected_email = 'validlogin@example.com'
        expected_first_name = 'Valid'
        expected_last_name = 'User'
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['message'] == expected_message
        assert response_data['user']['email'] == expected_email
        assert response_data['user']['first_name'] == expected_first_name
        assert response_data['user']['last_name'] == expected_last_name
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_login_success_returns_correct_response_structure(self, table_data_manager):
        """
        Test: Successful login returns correct JSON structure
        Input: POST request with valid credentials
        Expected Output: Response contains message, user, token_info fields
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'structure@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Structure'
        }
        client.post('/register/', user_data)
        
        login_data = {
            'email': 'structure@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 200
        expected_main_fields = ['message', 'user', 'token_info']
        expected_user_fields = ['email', 'first_name', 'last_name']
        expected_token_fields = ['slt_expires_in_seconds', 'slt_expires_at']
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        for field in expected_main_fields:
            assert field in response_data
        for field in expected_user_fields:
            assert field in response_data['user']
        for field in expected_token_fields:
            assert field in response_data['token_info']
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_login_success_sets_cookies(self, table_data_manager):
        """
        Test: Successful login sets LLT and SLT cookies
        Input: POST request with valid credentials
        Expected Output: Response has both llt and slt cookies
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'cookies@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Cookie'
        }
        client.post('/register/', user_data)
        
        login_data = {
            'email': 'cookies@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 200
        expected_cookies = ['llt', 'slt']
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        for cookie_name in expected_cookies:
            assert cookie_name in response.cookies
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_login_success_token_expiry_calculation(self, table_data_manager):
        """
        Test: Token expiry times are calculated correctly
        Input: POST request with valid credentials
        Expected Output: slt_expires_in_seconds is SLT_EXPIRY_MINUTES * 60
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'expiry@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Expiry'
        }
        client.post('/register/', user_data)
        
        login_data = {
            'email': 'expiry@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 200
        expected_expires_seconds = 15 * 60  # SLT_EXPIRY_MINUTES is typically 15
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['token_info']['slt_expires_in_seconds'] == expected_expires_seconds
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_login_success_excludes_sensitive_data(self, table_data_manager):
        """
        Test: Successful login excludes password from response
        Input: POST request with valid credentials
        Expected Output: Response does not contain password field
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'secure@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Secure'
        }
        client.post('/register/', user_data)
        
        login_data = {
            'email': 'secure@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 200
        excluded_field = 'password'
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        response_str = json.dumps(response_data)
        assert excluded_field not in response_str
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_login_missing_email_field(self, table_data_manager):
        """
        Test: Login fails when email is missing
        Input: POST request without email field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        login_data = {
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'email' in response_data

    def test_login_missing_password_field(self, table_data_manager):
        """
        Test: Login fails when password is missing
        Input: POST request without password field
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        login_data = {
            'email': 'test@example.com'
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'password' in response_data

    def test_login_invalid_email_format(self, table_data_manager):
        """
        Test: Login fails with invalid email format
        Input: POST request with malformed email
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        login_data = {
            'email': 'invalid-email-format',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'email' in response_data

    def test_login_non_existent_email(self, table_data_manager):
        """
        Test: Login fails with non-existent email
        Input: POST request with email that doesn't exist in database
        Expected Output: 400 error response with generic message
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 400
        expected_error = ['Invalid email or password']
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'non_field_errors' in response_data
        assert response_data['non_field_errors'] == expected_error

    def test_login_incorrect_password(self, table_data_manager):
        """
        Test: Login fails with incorrect password
        Input: POST request with valid email but wrong password
        Expected Output: 400 error response with generic message
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'wrongpass@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Wrong'
        }
        client.post('/register/', user_data)
        
        login_data = {
            'email': 'wrongpass@example.com',
            'password': 'WrongPassword456!'
        }
        
        # Expected output
        expected_status = 400
        expected_error = ['Invalid email or password']
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'non_field_errors' in response_data
        assert response_data['non_field_errors'] == expected_error
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_login_inactive_user(self, table_data_manager):
        """
        Test: Login fails with inactive user
        Input: POST request with credentials for inactive user
        Expected Output: 400 error response with generic message
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'inactive@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Inactive'
        }
        client.post('/register/', user_data)
        
        # Make user inactive
        user = User.objects.get(email='inactive@example.com')
        user.is_active = False
        user.save()
        
        login_data = {
            'email': 'inactive@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 400
        expected_error = ['Invalid email or password']
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert 'non_field_errors' in response_data
        assert response_data['non_field_errors'] == expected_error
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_login_empty_request_body(self, table_data_manager):
        """
        Test: Login fails with empty request body
        Input: POST request with no data
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        login_data = {}
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status

    def test_login_empty_values(self, table_data_manager):
        """
        Test: Login fails with empty values in fields
        Input: POST request with empty string values
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        login_data = {
            'email': '',
            'password': ''
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status

    def test_login_empty_string_values(self, table_data_manager):
        """
        Test: Login fails with empty string values
        Input: POST request with empty strings for email and password
        Expected Output: 400 error response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        login_data = {
            'email': '',
            'password': ''
        }
        
        # Expected output
        expected_status = 400
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status

    def test_login_extra_fields_ignored(self, table_data_manager):
        """
        Test: Login ignores extra unexpected fields
        Input: POST request with additional fields not in serializer
        Expected Output: 200 response ignoring extra fields
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'extralogin@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Extra'
        }
        client.post('/register/', user_data)
        
        login_data = {
            'email': 'extralogin@example.com',
            'password': 'ValidPassword123!',
            'unexpected_field': 'should_be_ignored',
            'another_field': 'also_ignored'
        }
        
        # Expected output
        expected_status = 200
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['user']['email'] == 'extralogin@example.com'
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_login_cookie_attributes(self, table_data_manager):
        """
        Test: Login sets cookies with correct attributes
        Input: POST request with valid credentials
        Expected Output: Cookies have httponly=True and correct paths
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'cookieattr@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Cookie'
        }
        client.post('/register/', user_data)
        
        login_data = {
            'email': 'cookieattr@example.com',
            'password': 'ValidPassword123!'
        }
        
        # Expected output
        expected_status = 200
        expected_httponly = True
        expected_path = '/'
        
        # Process
        response = client.post('/login/', login_data)
        
        # Compare output
        assert response.status_code == expected_status
        llt_cookie = response.cookies['llt']
        slt_cookie = response.cookies['slt']
        assert llt_cookie['httponly'] == expected_httponly
        assert slt_cookie['httponly'] == expected_httponly
        assert llt_cookie['path'] == expected_path
        assert slt_cookie['path'] == expected_path
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

 


@pytest.mark.integration
@pytest.mark.requires_db
class TestRefreshToken:



    def test_refresh_token_without_user_data_returns_401(self, table_data_manager):
        """
        Test: Request without user_data returns 401
        Input: GET request without user_data attribute
        Expected Output: 401 Unauthorized with redirect_to_login flag
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        # No user_data set on request
        
        # Expected output
        expected_status = 401
        expected_error = 'No valid token found'
        expected_redirect = True
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['error'] == expected_error
        assert response_data['redirect_to_login'] == expected_redirect

    def test_refresh_token_success_with_complete_user_data(self, table_data_manager):
        """
        Test: Successful token refresh with complete user data
        Input: GET request with complete user_data
        Expected Output: 200 response with token info
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'complete@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Complete',
            'last_name': 'User'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='complete@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_message = 'Token refreshed successfully'
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['message'] == expected_message
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_success_with_minimal_user_data(self, table_data_manager):
        """
        Test: Successful token refresh with minimal user data
        Input: GET request with required user_data fields only
        Expected Output: 200 response with token info
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'minimal@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Minimal'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='minimal@example.com')
        
        # Create a mock request with minimal user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name
        }
        
        # Expected output
        expected_status = 200
        expected_message = 'Token refreshed successfully'
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['message'] == expected_message
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_success_returns_correct_response_structure(self, table_data_manager):
        """
        Test: Successful token refresh returns correct JSON structure
        Input: GET request with valid user_data
        Expected Output: Response contains message and token_info fields
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'structure@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Structure'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='structure@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_main_fields = ['message', 'token_info']
        expected_token_fields = ['slt_expires_in_seconds', 'slt_expires_at']
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        for field in expected_main_fields:
            assert field in response_data
        for field in expected_token_fields:
            assert field in response_data['token_info']
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_success_sets_slt_cookie(self, table_data_manager):
        """
        Test: Successful token refresh sets new SLT cookie
        Input: GET request with valid user_data
        Expected Output: Response has updated slt cookie
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'cookie@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Cookie'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='cookie@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_cookie = 'slt'
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        assert expected_cookie in response.cookies
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_cookie_attributes(self, table_data_manager):
        """
        Test: Token refresh sets SLT cookie with correct attributes
        Input: GET request with valid user_data
        Expected Output: SLT cookie has httponly=True and correct path
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'cookieattr@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Cookie'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='cookieattr@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_httponly = True
        expected_path = '/'
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        slt_cookie = response.cookies['slt']
        assert slt_cookie['httponly'] == expected_httponly
        assert slt_cookie['path'] == expected_path
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_expiry_calculation(self, table_data_manager):
        """
        Test: Token expiry times are calculated correctly
        Input: GET request with valid user_data
        Expected Output: slt_expires_in_seconds is SLT_EXPIRY_MINUTES * 60
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'expiry@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Expiry'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='expiry@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_expires_seconds = 15 * 60  # SLT_EXPIRY_MINUTES is typically 15
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['token_info']['slt_expires_in_seconds'] == expected_expires_seconds
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_datetime_format(self, table_data_manager):
        """
        Test: Token expiry datetime is in correct ISO format
        Input: GET request with valid user_data
        Expected Output: slt_expires_at ends with 'Z' and is valid ISO format
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'datetime@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'DateTime'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='datetime@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_suffix = 'Z'
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        expires_at = response_data['token_info']['slt_expires_at']
        assert expires_at.endswith(expected_suffix)
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_missing_first_name_handled_gracefully(self, table_data_manager):
        """
        Test: Token refresh handles missing first_name gracefully
        Input: GET request with user_data missing first_name
        Expected Output: 200 response with None for first_name
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'nofirst@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'NoFirst'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='nofirst@example.com')
        
        # Create a mock request with user_data missing first_name
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_message = 'Token refreshed successfully'
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['message'] == expected_message
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_missing_last_name_handled_gracefully(self, table_data_manager):
        """
        Test: Token refresh handles missing last_name gracefully
        Input: GET request with user_data missing last_name
        Expected Output: 200 response with None for last_name
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'nolast@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'NoLast'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='nolast@example.com')
        
        # Create a mock request with user_data missing last_name
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name
        }
        
        # Expected output
        expected_status = 200
        expected_message = 'Token refreshed successfully'
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['message'] == expected_message
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_refresh_token_excludes_sensitive_data(self, table_data_manager):
        """
        Test: Token refresh excludes sensitive tokens from response body
        Input: GET request with valid user_data
        Expected Output: Response does not contain token values in body
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'secure@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Secure'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='secure@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/refresh-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        
        # Process
        response = refresh_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        
        # Should not contain actual JWT tokens or raw token fields
        assert 'llt' not in response_data
        assert 'slt' not in response_data
        assert 'access_token' not in response_data
        assert 'refresh_token' not in response_data
        assert 'token' not in response_data
        
        # Should only contain token_info with expiry details
        assert 'token_info' in response_data
        assert 'slt_expires_in_seconds' in response_data['token_info']
        assert 'slt_expires_at' in response_data['token_info']
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

 


@pytest.mark.integration
@pytest.mark.requires_db
class TestGetWebsocketToken:



    def test_get_websocket_token_without_user_data_returns_401(self, table_data_manager):
        """
        Test: Request without user_data returns 401
        Input: GET request without user_data attribute
        Expected Output: 401 Unauthorized with redirect_to_login flag
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/websocket-token/')
        # No user_data set on request
        
        # Expected output
        expected_status = 401
        expected_error = 'No valid token found'
        expected_redirect = True
        
        # Process
        response = get_websocket_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['error'] == expected_error
        assert response_data['redirect_to_login'] == expected_redirect

    def test_get_websocket_token_success_with_complete_user_data(self, table_data_manager):
        """
        Test: Successful websocket token generation with complete user data
        Input: GET request with complete user_data
        Expected Output: 200 response with websocket token and user info
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'wscomplete@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Complete',
            'last_name': 'WebSocket'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='wscomplete@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/websocket-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_email = 'wscomplete@example.com'
        expected_first_name = 'Complete'
        expected_last_name = 'WebSocket'
        
        # Process
        response = get_websocket_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['user']['email'] == expected_email
        assert response_data['user']['first_name'] == expected_first_name
        assert response_data['user']['last_name'] == expected_last_name
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_get_websocket_token_contains_actual_token(self, table_data_manager):
        """
        Test: Websocket token response contains actual token value
        Input: GET request with valid user_data
        Expected Output: 'token' field contains non-empty string
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'wstoken@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Token'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='wstoken@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/websocket-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        
        # Process
        response = get_websocket_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert 'token' in response_data
        assert response_data['token'] is not None
        assert len(response_data['token']) > 0
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_get_websocket_token_no_cookies_set(self, table_data_manager):
        """
        Test: Websocket token does not set any cookies
        Input: GET request with valid user_data
        Expected Output: Response has no cookies (token only in body)
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'wsnocookie@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'NoCookie'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='wsnocookie@example.com')
        
        # Create a mock request with user_data
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/websocket-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_cookie_count = 0
        
        # Process
        response = get_websocket_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        assert len(response.cookies) == expected_cookie_count
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_get_websocket_token_missing_first_name_handled_gracefully(self, table_data_manager):
        """
        Test: Websocket token handles missing first_name gracefully
        Input: GET request with user_data missing first_name
        Expected Output: 200 response with None for first_name
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'wsnofirst@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'NoFirst'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='wsnofirst@example.com')
        
        # Create a mock request with user_data missing first_name
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/websocket-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'last_name': user.last_name
        }
        
        # Expected output
        expected_status = 200
        expected_email = 'wsnofirst@example.com'
        
        # Process
        response = get_websocket_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['user']['email'] == expected_email
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_get_websocket_token_missing_last_name_handled_gracefully(self, table_data_manager):
        """
        Test: Websocket token handles missing last_name gracefully
        Input: GET request with user_data missing last_name
        Expected Output: 200 response with None for last_name
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create a user first
        user_data = {
            'email': 'wsnolast@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'NoLast'
        }
        client.post('/register/', user_data)
        user = User.objects.get(email='wsnolast@example.com')
        
        # Create a mock request with user_data missing last_name
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/websocket-token/')
        request.user_data = {
            'public_id': str(user.public_id),
            'email': user.email,
            'first_name': user.first_name
        }
        
        # Expected output
        expected_status = 200
        expected_email = 'wsnolast@example.com'
        
        # Process
        response = get_websocket_token(request)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.data
        assert response_data['user']['email'] == expected_email
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

 


@pytest.mark.integration
@pytest.mark.requires_db
class TestLogout:



    def test_logout_successful_response(self, table_data_manager):
        """
        Test: Successful logout with correct response message
        Input: POST request to logout endpoint
        Expected Output: 200 response with success message
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        
        # Expected output
        expected_status = 200
        expected_message = 'Logout successful'
        
        # Process
        response = client.post('/logout/')
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['message'] == expected_message

    def test_logout_clears_authentication_cookies(self, table_data_manager):
        """
        Test: Logout clears LLT and SLT cookies
        Input: POST request after login (with cookies set)
        Expected Output: Cookies are deleted in logout response
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create user and login first to set cookies
        user_data = {
            'email': 'logoutcookie@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'Logout'
        }
        client.post('/register/', user_data)
        client.post('/login/', {
            'email': 'logoutcookie@example.com',
            'password': 'ValidPassword123!'
        })
        
        # Expected output
        expected_status = 200
        expected_deleted_cookies = ['llt', 'slt']
        
        # Process
        response = client.post('/logout/')
        
        # Compare output
        assert response.status_code == expected_status
        for cookie_name in expected_deleted_cookies:
            assert cookie_name in response.cookies
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_logout_without_prior_login(self, table_data_manager):
        """
        Test: Logout works without prior login
        Input: POST request to logout without previous authentication
        Expected Output: 200 response with success message
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        
        # Expected output
        expected_status = 200
        expected_message = 'Logout successful'
        
        # Process
        response = client.post('/logout/')
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['message'] == expected_message

    def test_logout_multiple_consecutive_calls(self, table_data_manager):
        """
        Test: Multiple logout calls work without errors
        Input: Multiple consecutive POST requests to logout
        Expected Output: All calls return 200 with success message
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        
        # Expected output
        expected_status = 200
        expected_message = 'Logout successful'
        
        # Process - Call logout multiple times
        first_response = client.post('/logout/')
        second_response = client.post('/logout/')
        third_response = client.post('/logout/')
        
        # Compare output
        assert first_response.status_code == expected_status
        assert second_response.status_code == expected_status
        assert third_response.status_code == expected_status
        
        first_data = first_response.json()
        second_data = second_response.json()
        third_data = third_response.json()
        
        assert first_data['message'] == expected_message
        assert second_data['message'] == expected_message
        assert third_data['message'] == expected_message

    def test_logout_with_request_data_ignored(self, table_data_manager):
        """
        Test: Logout ignores request body data
        Input: POST request with extra data in request body
        Expected Output: 200 response (data ignored, no validation)
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        request_data = {
            'extra_field': 'should_be_ignored',
            'another_field': 'also_ignored'
        }
        
        # Expected output
        expected_status = 200
        expected_message = 'Logout successful'
        
        # Process
        response = client.post('/logout/', request_data)
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert response_data['message'] == expected_message

    def test_refresh_token_fails_after_logout(self, table_data_manager):
        """
        Test: Refresh token endpoint fails after logout
        Input: Login, logout, then attempt refresh token
        Expected Output: Refresh token returns 401 after logout
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create user and login first
        user_data = {
            'email': 'refreshlogout@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'RefreshLogout'
        }
        client.post('/register/', user_data)
        login_response = client.post('/login/', {
            'email': 'refreshlogout@example.com',
            'password': 'ValidPassword123!'
        })
        
        # Logout
        logout_response = client.post('/logout/')
        
        # Expected output
        expected_login_status = 200
        expected_logout_status = 200
        expected_refresh_status = 401
        
        # Process - Try to refresh token after logout
        refresh_response = client.get('/refresh-token/')
        
        # Compare output
        assert login_response.status_code == expected_login_status
        assert logout_response.status_code == expected_logout_status
        assert refresh_response.status_code == expected_refresh_status
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_websocket_token_fails_after_logout(self, table_data_manager):
        """
        Test: WebSocket token endpoint fails after logout
        Input: Login, logout, then attempt to get websocket token
        Expected Output: WebSocket token returns 401 after logout
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        # Create user and login first
        user_data = {
            'email': 'wslogout@example.com',
            'password': 'ValidPassword123!',
            'first_name': 'WSLogout'
        }
        client.post('/register/', user_data)
        login_response = client.post('/login/', {
            'email': 'wslogout@example.com',
            'password': 'ValidPassword123!'
        })
        
        # Logout
        logout_response = client.post('/logout/')
        
        # Expected output
        expected_login_status = 200
        expected_logout_status = 200
        expected_ws_token_status = 401
        
        # Process - Try to get websocket token after logout
        ws_token_response = client.get('/websocket-token/')
        
        # Compare output
        assert login_response.status_code == expected_login_status
        assert logout_response.status_code == expected_logout_status
        assert ws_token_response.status_code == expected_ws_token_status
        
        # Cleanup
        table_data_manager.clear_table_completely('users')

    def test_logout_response_structure(self, table_data_manager):
        """
        Test: Logout response has correct JSON structure
        Input: POST request to logout endpoint
        Expected Output: Response contains only message field
        """
        # Setup test data
        table_data_manager.clear_table_completely('users')
        
        # Input
        client = Client()
        
        # Expected output
        expected_status = 200
        expected_fields = ['message']
        expected_field_count = 1
        
        # Process
        response = client.post('/logout/')
        
        # Compare output
        assert response.status_code == expected_status
        response_data = response.json()
        assert len(response_data) == expected_field_count
        for field in expected_fields:
            assert field in response_data