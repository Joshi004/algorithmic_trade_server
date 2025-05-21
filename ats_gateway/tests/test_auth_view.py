"""
Test module for authentication views in the ATS Gateway.

This module contains unit tests for the authentication-related views,
focusing on the login endpoint which handles user authentication and token generation.
The tests verify API behavior, response formats, error handling, and proper token generation.

These tests use Django's test client to simulate HTTP requests and use mocking
to isolate the view logic from the serializer and token generation functions.
"""

import json
import uuid
import jwt
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from ..utils.jwt_utils import LLT_SECRET_KEY, SLT_SECRET_KEY


class AuthViewTestCase(TestCase):
    """Test cases for authentication views.
    
    This test case validates the behavior of authentication-related views, focusing on:
    - Login functionality and token generation
    - HTTP status codes and response formats
    - Error handling for invalid credentials
    - Token payload contents and validation
    - HTTP method validation
    
    The tests use Django's test client to make requests to the API endpoints and
    mock the serializers and token generation functions to isolate the view logic.
    """

    def setUp(self):
        """Set up test case data.
        
        Initializes the test client, defines API endpoint URLs, and creates
        test user data to be used in authentication tests.
        """
        self.client = Client()
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        self.refresh_token_url = reverse('refresh_token')
        
        # Test user data
        self.test_email = "test@example.com"
        self.test_password = "Password123!"
        self.test_public_id = str(uuid.uuid4())
        
        # Mock response data for serializer
        self.mock_validated_data = {
            'public_id': self.test_public_id,
            'email': self.test_email,
        }

    @patch('ats_gateway.views.AuthView.LoginSerializer')
    def test_login_success(self, MockLoginSerializer):
        """Test successful login request.
        
        Verifies that:
        1. The view returns a 200 OK status code on successful login
        2. The response contains both long-lived and short-lived tokens
        3. The tokens contain the correct user information
        4. The tokens are properly encoded with the correct secret keys
        5. The tokens have the correct token type fields
        
        This test mocks the serializer to simulate successful validation.
        """
        # Configure the mock serializer
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.is_valid.return_value = True
        mock_serializer_instance.validated_data = self.mock_validated_data
        MockLoginSerializer.return_value = mock_serializer_instance
        
        # Perform login request
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.test_email,
                'password': self.test_password
            }),
            content_type='application/json'
        )
        
        # Validate response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('long_lived_token', response.data)
        self.assertIn('short_lived_token', response.data)
        
        # Verify tokens
        long_lived_token = response.data['long_lived_token']
        short_lived_token = response.data['short_lived_token']
        
        # Decode and validate token payloads
        llt_payload = jwt.decode(long_lived_token, LLT_SECRET_KEY, algorithms=['HS256'])
        slt_payload = jwt.decode(short_lived_token, SLT_SECRET_KEY, algorithms=['HS256'])
        
        # Validate token payload content
        self.assertEqual(llt_payload['public_id'], self.test_public_id)
        self.assertEqual(llt_payload['email'], self.test_email)
        self.assertEqual(llt_payload['token_type'], 'long_lived')
        
        self.assertEqual(slt_payload['public_id'], self.test_public_id)
        self.assertEqual(slt_payload['email'], self.test_email)
        self.assertEqual(slt_payload['token_type'], 'short_lived')

    @patch('ats_gateway.views.AuthView.LoginSerializer')
    def test_login_invalid_credentials(self, MockLoginSerializer):
        """Test login with invalid credentials.
        
        Verifies that:
        1. The view returns a 400 Bad Request status code for invalid credentials
        2. The response contains appropriate error messages
        3. The serializer validation errors are passed through to the response
        
        This test mocks the serializer to simulate validation failure due to invalid credentials.
        """
        # Configure the mock serializer to fail validation
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.is_valid.return_value = False
        mock_serializer_instance.errors = {'non_field_errors': ['Invalid email or password']}
        MockLoginSerializer.return_value = mock_serializer_instance
        
        # Perform login request
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.test_email,
                'password': 'WrongPassword'
            }),
            content_type='application/json'
        )
        
        # Validate response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_login_missing_fields(self):
        """Test login with missing fields.
        
        Verifies that:
        1. The view returns a 400 Bad Request status code when required fields are missing
        2. The API rejects requests missing the email field
        3. The API rejects requests missing the password field
        4. The API rejects empty requests
        
        Tests the view's handling of incomplete requests without mocking.
        """
        # Test missing email
        response1 = self.client.post(
            self.login_url,
            data=json.dumps({'password': self.test_password}),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test missing password
        response2 = self.client.post(
            self.login_url,
            data=json.dumps({'email': self.test_email}),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test empty request
        response3 = self.client.post(
            self.login_url,
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response3.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_incorrect_method(self):
        """Test login with incorrect HTTP method.
        
        Verifies that:
        1. The login endpoint only accepts POST requests
        2. GET requests to the login endpoint are rejected with 405 Method Not Allowed
        
        Tests the view's HTTP method restrictions.
        """
        # Test with GET method (should be POST)
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch('ats_gateway.views.AuthView.generate_long_lived_token')
    @patch('ats_gateway.views.AuthView.generate_short_lived_token')
    @patch('ats_gateway.views.AuthView.LoginSerializer')
    def test_token_generation_in_login(self, MockLoginSerializer, mock_generate_short_lived, mock_generate_long_lived):
        """Test that login calls token generation functions with correct parameters.
        
        Verifies that:
        1. The login view calls both token generation functions
        2. The functions are called with the correct user data
        3. The generated tokens are included in the response
        4. The view correctly formats the response
        
        Uses mocking to verify the interaction between the view and token generation functions.
        """
        # Configure mocks
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.is_valid.return_value = True
        mock_serializer_instance.validated_data = self.mock_validated_data
        MockLoginSerializer.return_value = mock_serializer_instance
        
        # Mock token generation functions
        mock_generate_long_lived.return_value = "long-lived-token"
        mock_generate_short_lived.return_value = "short-lived-token"
        
        # Perform login request
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.test_email,
                'password': self.test_password
            }),
            content_type='application/json'
        )
        
        # Check that token generation functions were called with correct params
        user_data = {
            "public_id": self.test_public_id,
            "email": self.test_email
        }
        mock_generate_long_lived.assert_called_once_with(user_data)
        mock_generate_short_lived.assert_called_once_with(user_data)
        
        # Validate response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['long_lived_token'], "long-lived-token")
        self.assertEqual(response.data['short_lived_token'], "short-lived-token")
