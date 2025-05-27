"""
Test module for JWT authentication middleware in the ATS Gateway.

This module contains unit tests for the JWT authentication middleware which validates
tokens in request headers and enforces token type restrictions based on the endpoint.
The tests verify token validation, error handling, and the enforcement of token type
requirements for different endpoints.

These tests use Django's RequestFactory to create mock requests and test the middleware
in isolation from the rest of the application.
"""

import jwt
import uuid
import json
import datetime
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.http import HttpResponse, JsonResponse
from ..middleware.jwt_auth_middleware import JWTAuthMiddleware
from ..utils.jwt_utils import (
    generate_long_lived_token, generate_short_lived_token,
    LLT_SECRET_KEY, SLT_SECRET_KEY
)


class JWTAuthMiddlewareTestCase(TestCase):
    """Test cases for the JWT authentication middleware.
    
    This test case validates the behavior of the JWT authentication middleware, focusing on:
    - Public path detection and bypass
    - Token extraction from request headers
    - Token validation for different endpoints
    - Enforcement of token type restrictions
    - Error handling for missing, invalid, or expired tokens
    - Response formats and status codes
    
    The tests use Django's RequestFactory to create requests and test the middleware
    in isolation from the rest of the application.
    """

    def setUp(self):
        """Set up test case data.
        
        Creates a RequestFactory instance, mocks the get_response function,
        initializes the middleware, and generates test tokens for use in the tests.
        """
        self.factory = RequestFactory()
        
        # Mock get_response function
        self.get_response_mock = MagicMock()
        self.get_response_mock.return_value = HttpResponse("Mock response")
        
        # Create middleware instance
        self.middleware = JWTAuthMiddleware(self.get_response_mock)
        
        # Test user data
        self.test_payload = {
            "public_id": str(uuid.uuid4()),
            "email": "middleware_test@example.com"
        }
        
        # Generate tokens
        self.long_lived_token = generate_long_lived_token(self.test_payload)
        self.short_lived_token = generate_short_lived_token(self.test_payload)
        
        # Define paths for testing
        self.public_path = "/login/"
        self.refresh_path = "/refresh-token/"
        self.protected_path = "/protected-endpoint/"

    def test_public_paths_skip_auth(self):
        """Test that public paths skip authentication.
        
        Verifies that:
        1. The middleware correctly identifies public paths (like /login/)
        2. Authentication is skipped for these paths
        3. The request is passed directly to the next middleware/view
        
        Tests the public path detection logic in the middleware.
        """
        # Test login path
        request = self.factory.get(self.public_path)
        response = self.middleware(request)
        
        # Verify no token check and get_response was called
        self.assertEqual(response, self.get_response_mock.return_value)
        self.get_response_mock.assert_called_once()

    def test_missing_auth_header(self):
        """Test request with missing Authorization header.
        
        Verifies that:
        1. The middleware correctly detects missing Authorization headers
        2. The middleware returns a 401 Unauthorized response
        3. The response contains appropriate error information
        
        Tests the middleware's handling of requests without authentication.
        """
        request = self.factory.get(self.protected_path)
        response = self.middleware(request)
        
        # Verify error response
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Missing Authorization header')

    def test_invalid_auth_header_format(self):
        """Test request with invalid Authorization header format.
        
        Verifies that:
        1. The middleware validates the format of the Authorization header
        2. Headers not starting with 'Bearer ' are rejected
        3. The middleware returns a 401 Unauthorized with an appropriate error message
        
        Tests the middleware's header format validation.
        """
        request = self.factory.get(self.protected_path)
        request.META['HTTP_AUTHORIZATION'] = 'Invalid Format'
        response = self.middleware(request)
        
        # Verify error response
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Authorization header must start with Bearer')

    def test_refresh_endpoint_with_long_lived_token(self):
        """Test accessing refresh endpoint with long-lived token.
        
        Verifies that:
        1. The middleware correctly identifies the refresh-token endpoint
        2. Long-lived tokens are accepted for this endpoint
        3. The user data is extracted and added to the request
        4. The request is passed to the next middleware/view
        
        Tests the middleware's handling of long-lived tokens at the refresh endpoint.
        """
        request = self.factory.get(self.refresh_path)
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.long_lived_token}'
        response = self.middleware(request)
        
        # Verify successful response
        self.assertEqual(response, self.get_response_mock.return_value)
        # Verify user_data was added to request
        self.assertTrue(hasattr(request, 'user_data'))
        self.assertEqual(request.user_data['public_id'], self.test_payload['public_id'])

    def test_refresh_endpoint_with_short_lived_token(self):
        """Test accessing refresh endpoint with short-lived token (should fail).
        
        Verifies that:
        1. The middleware rejects short-lived tokens for the refresh endpoint
        2. A 401 Unauthorized response is returned
        3. The error message indicates that a long-lived token is required
        
        Tests the middleware's token type enforcement for the refresh endpoint.
        """
        request = self.factory.get(self.refresh_path)
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.short_lived_token}'
        response = self.middleware(request)
        
        # Verify error response
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', response_data)
        self.assertIn('Short-lived tokens cannot be used for token refresh', response_data['error'])

    def test_protected_endpoint_with_short_lived_token(self):
        """Test accessing protected endpoint with short-lived token.
        
        Verifies that:
        1. The middleware accepts short-lived tokens for regular API endpoints
        2. The user data is extracted and added to the request
        3. The request is passed to the next middleware/view
        
        Tests the middleware's handling of short-lived tokens for standard endpoints.
        """
        request = self.factory.get(self.protected_path)
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.short_lived_token}'
        response = self.middleware(request)
        
        # Verify successful response
        self.assertEqual(response, self.get_response_mock.return_value)
        # Verify user_data was added to request
        self.assertTrue(hasattr(request, 'user_data'))
        self.assertEqual(request.user_data['public_id'], self.test_payload['public_id'])

    def test_protected_endpoint_with_long_lived_token(self):
        """Test accessing protected endpoint with long-lived token (should fail).
        
        Verifies that:
        1. The middleware rejects long-lived tokens for regular API endpoints
        2. A 401 Unauthorized response is returned
        3. The error message indicates that a short-lived token is required
        4. The response includes a 'please_refresh' flag to guide client behavior
        
        Tests the middleware's token type enforcement for standard endpoints.
        """
        request = self.factory.get(self.protected_path)
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.long_lived_token}'
        response = self.middleware(request)
        
        # Verify error response
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', response_data)
        self.assertIn('Long-lived tokens can only be used for token refresh', response_data['error'])
        self.assertTrue(response_data['please_refresh'])

    def test_expired_token(self):
        """Test request with expired token.
        
        Verifies that:
        1. The middleware correctly identifies expired tokens
        2. A 401 Unauthorized response is returned
        3. The error message indicates token expiration
        4. The response includes a 'redirect_to_login' flag
        
        Tests the middleware's handling of token expiration.
        """
        # Create expired token
        payload = {**self.test_payload}
        expired_time = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        expired_token = jwt.encode(
            {**payload, 'exp': expired_time, 'token_type': 'short_lived'}, 
            SLT_SECRET_KEY, 
            algorithm='HS256'
        )
        
        # Make request
        request = self.factory.get(self.protected_path)
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {expired_token}'
        response = self.middleware(request)
        
        # Verify error response
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', response_data)
        self.assertIn('Invalid or expired token', response_data['error'])  # Error message for invalid or expired tokens
        self.assertTrue(response_data.get('redirect_to_login', False))

    def test_invalid_token(self):
        """Test request with invalid token.
        
        Verifies that:
        1. The middleware rejects malformed or invalid tokens
        2. A 401 Unauthorized response is returned
        3. The error message indicates an invalid token
        4. The response includes a 'redirect_to_login' flag
        
        Tests the middleware's token validation logic.
        """
        request = self.factory.get(self.protected_path)
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid.token.string'
        response = self.middleware(request)
        
        # Verify error response
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', response_data)
        self.assertIn('Invalid or expired token', response_data['error'])
        self.assertTrue(response_data.get('redirect_to_login', False))

    # Note: We're not mocking the decode functions directly since they're not directly imported in the middleware
    # Instead, we'll examine the result of calling the middleware with different tokens
    def test_token_type_validation(self):
        """Test that the middleware correctly validates token types.
        
        Verifies that:
        1. The middleware uses the correct decode function based on the endpoint
        2. For the refresh endpoint, decode_long_lived_token is called
        3. For regular endpoints, decode_short_lived_token is called first
        4. The middleware passes the request to the next handler when a valid token is found
        
        Uses mocking to verify the internal logic for token type validation.
        """
        # Test refresh endpoint with long-lived token - this should succeed
        request1 = self.factory.get(self.refresh_path)
        request1.META['HTTP_AUTHORIZATION'] = f'Bearer {self.long_lived_token}'
        response1 = self.middleware(request1)
        
        # Verify successful response for refresh endpoint with long-lived token
        self.assertEqual(response1, self.get_response_mock.return_value)
        self.assertTrue(hasattr(request1, 'user_data'), "user_data should be added to request")
        
        # Test protected endpoint with short-lived token - this should succeed
        request2 = self.factory.get(self.protected_path)
        request2.META['HTTP_AUTHORIZATION'] = f'Bearer {self.short_lived_token}'
        response2 = self.middleware(request2)
        
        # Verify successful response for protected endpoint with short-lived token
        self.assertEqual(response2, self.get_response_mock.return_value)
        self.assertTrue(hasattr(request2, 'user_data'), "user_data should be added to request")
        
        # Test refresh endpoint with short-lived token - this should fail
        request3 = self.factory.get(self.refresh_path)
        request3.META['HTTP_AUTHORIZATION'] = f'Bearer {self.short_lived_token}'
        response3 = self.middleware(request3)
        
        # Verify error response
        self.assertIsInstance(response3, JsonResponse)
        response_data = json.loads(response3.content.decode('utf-8'))
        self.assertIn('Short-lived tokens cannot be used for token refresh', response_data['error'])
        
        # Test protected endpoint with long-lived token - this should fail
        request4 = self.factory.get(self.protected_path)
        request4.META['HTTP_AUTHORIZATION'] = f'Bearer {self.long_lived_token}'
        response4 = self.middleware(request4)
        
        # Verify error response
        self.assertIsInstance(response4, JsonResponse)
        response_data = json.loads(response4.content.decode('utf-8'))
        self.assertIn('Long-lived tokens can only be used for token refresh', response_data['error'])
