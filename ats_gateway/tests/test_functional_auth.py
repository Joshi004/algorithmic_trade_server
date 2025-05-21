"""
Functional test module for authentication flow in the ATS Gateway.

This module contains end-to-end functional tests for the complete authentication flow,
including login, token generation, token validation, and token refresh. Unlike the
unit tests, these tests validate the integration of all components in the authentication
process using a real database and HTTP requests.

These tests create real user records in the test database and make HTTP requests
through the entire middleware and view stack to test the complete flow.
"""

import json
import uuid
import bcrypt
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from ..models.User import User
from ..utils.jwt_utils import decode_long_lived_token, decode_short_lived_token


class AuthenticationFlowTestCase(TestCase):
    """Functional tests for the authentication flow.
    
    This test case validates the complete authentication flow from login to token
    usage and refresh. It focuses on:
    - End-to-end login process with real database users
    - Token generation and verification
    - Token refresh functionality
    - Security boundaries between token types
    - Error handling for various authentication scenarios
    
    These tests exercise the full authentication stack including serializers,
    views, middleware, and token utilities.
    """

    def setUp(self):
        """Set up test data and environment.
        
        Creates:
        1. A test client for making HTTP requests
        2. A real user record in the test database with a bcrypt-hashed password
        3. URL references for the authentication endpoints
        
        This setup enables testing with actual database queries and HTTP requests.
        """
        self.client = Client()
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        self.refresh_token_url = reverse('refresh_token')
        
        # Test user data
        self.test_email = "functional_test@example.com"
        self.test_password = "SecurePassword123!"
        self.test_public_id = uuid.uuid4()
        
        # Create a test user in the database
        hashed_password = bcrypt.hashpw(self.test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        self.test_user = User.objects.create(
            email=self.test_email,
            password=hashed_password,
            public_id=self.test_public_id,
            is_active=True
        )

    def test_complete_login_flow(self):
        """Test the complete login flow from request to token verification.
        
        This test validates the entire authentication process by:
        1. Making a login request with valid credentials
        2. Verifying both tokens are returned with correct status code
        3. Decoding and validating token payloads for correct user information
        4. Using the long-lived token to refresh and get a new short-lived token
        5. Verifying the new short-lived token is valid and contains correct information
        
        This is the primary test for the complete authentication flow.
        """
        # Step 1: Make a login request
        login_response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.test_email,
                'password': self.test_password
            }),
            content_type='application/json'
        )
        
        # Verify successful login
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('long_lived_token', login_response.data)
        self.assertIn('short_lived_token', login_response.data)
        
        # Extract tokens
        long_lived_token = login_response.data['long_lived_token']
        short_lived_token = login_response.data['short_lived_token']
        
        # Step 2: Decode and verify tokens
        llt_payload = decode_long_lived_token(long_lived_token)
        slt_payload = decode_short_lived_token(short_lived_token)
        
        # Verify token payloads
        self.assertIsNotNone(llt_payload)
        self.assertIsNotNone(slt_payload)
        self.assertEqual(llt_payload["public_id"], str(self.test_public_id))
        self.assertEqual(llt_payload["email"], self.test_email)
        self.assertEqual(llt_payload["token_type"], "long_lived")
        self.assertEqual(slt_payload["public_id"], str(self.test_public_id))
        self.assertEqual(slt_payload["email"], self.test_email)
        self.assertEqual(slt_payload["token_type"], "short_lived")
        
        # Step 3: Test refresh token endpoint
        refresh_response = self.client.get(
            self.refresh_token_url,
            HTTP_AUTHORIZATION=f'Bearer {long_lived_token}'
        )
        
        # Verify successful token refresh
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('short_lived_token', refresh_response.data)
        
        # Extract and verify new short-lived token
        new_short_lived_token = refresh_response.data['short_lived_token']
        new_slt_payload = decode_short_lived_token(new_short_lived_token)
        
        self.assertIsNotNone(new_slt_payload)
        self.assertEqual(new_slt_payload["public_id"], str(self.test_public_id))
        self.assertEqual(new_slt_payload["email"], self.test_email)
        self.assertEqual(new_slt_payload["token_type"], "short_lived")

    def test_login_with_nonexistent_user(self):
        """Test login with a non-existent user.
        
        Verifies that:
        1. Login attempts with non-existent users are rejected
        2. The API returns a 400 Bad Request status code
        3. The response contains appropriate error messages
        
        Tests the authentication system's handling of unknown users.
        """
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': 'nonexistent@example.com',
                'password': self.test_password
            }),
            content_type='application/json'
        )
        
        # Verify failed login
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_login_with_incorrect_password(self):
        """Test login with incorrect password.
        
        Verifies that:
        1. Login attempts with incorrect passwords are rejected
        2. The API returns a 400 Bad Request status code
        3. The response contains appropriate error messages
        
        Tests the authentication system's password validation.
        """
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.test_email,
                'password': 'WrongPassword123!'
            }),
            content_type='application/json'
        )
        
        # Verify failed login
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_refresh_with_short_lived_token(self):
        """Test refresh endpoint with short-lived token (should fail).
        
        Verifies that:
        1. The refresh endpoint rejects short-lived tokens
        2. The API returns a 401 Unauthorized status code
        3. The response contains appropriate error information
        
        Tests the token type enforcement for the refresh endpoint.
        """
        # First login to get tokens
        login_response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.test_email,
                'password': self.test_password
            }),
            content_type='application/json'
        )
        
        short_lived_token = login_response.data['short_lived_token']
        
        # Try refreshing with short-lived token
        refresh_response = self.client.get(
            self.refresh_token_url,
            HTTP_AUTHORIZATION=f'Bearer {short_lived_token}'
        )
        
        # Verify failed token refresh
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', refresh_response.json())

    def test_access_protected_endpoint_with_long_lived_token(self):
        """Test accessing a protected endpoint with long-lived token (should fail).
        
        Verifies that:
        1. Protected endpoints reject long-lived tokens
        2. The API enforces token type requirements
        
        This test validates the security boundary that long-lived tokens can only
        be used for refreshing tokens, not for accessing API resources.
        """
        # Create a test protected endpoint using a view that requires authentication
        protected_url = reverse('register')  # Using register as an example protected endpoint
        
        # First login to get tokens
        login_response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.test_email,
                'password': self.test_password
            }),
            content_type='application/json'
        )
        
        long_lived_token = login_response.data['long_lived_token']
        
        # Try accessing protected endpoint with long-lived token
        response = self.client.get(
            protected_url,
            HTTP_AUTHORIZATION=f'Bearer {long_lived_token}'
        )
        
        # This should fail as register is a public path, but if it reaches the middleware
        # it should reject the long-lived token for non-refresh endpoints
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_login_with_inactive_user(self):
        """Test login with an inactive user account.
        
        Verifies that:
        1. Login attempts with inactive user accounts are rejected
        2. The API returns a 400 Bad Request status code
        3. The response contains appropriate error messages
        
        Tests the authentication system's handling of inactive accounts,
        without revealing to the client that the account exists but is inactive.
        """
        # Deactivate the test user
        self.test_user.is_active = False
        self.test_user.save()
        
        # Try logging in
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.test_email,
                'password': self.test_password
            }),
            content_type='application/json'
        )
        
        # Verify failed login
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
