"""
Comprehensive tests for broker view in the Integration Service.

This module contains tests for the broker registration and management endpoints,
following a clear structure of setup, expected response definition, function execution,
and validation with direct equality comparisons.
"""

import json
import uuid
from django.test import Client, RequestFactory, TransactionTestCase
from django.db import connection
from rest_framework import status
from unittest.mock import patch

from integration_service.views.broker_view import register_broker, get_user_brokers, set_default_broker
from integration_service.models.UserBrokerCredential import UserBrokerCredential


class BrokerViewTest(TransactionTestCase):
    """Tests for broker view functions using real database operations."""

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def setUp(self, mock_is_public):
        """Set up test data using direct ORM operations."""
        # Initialize test clients
        self.client = Client()
        self.factory = RequestFactory()
        
        # Generate test data values
        self.test_user_id = str(uuid.uuid4())
        self.test_broker_name = 'zerodha'
        
        # API endpoints
        self.register_broker_url = '/integration/register_broker/'
        self.get_user_brokers_url = '/integration/get_user_brokers/'
        self.set_default_broker_url = '/integration/set_default_broker/'
        
        # Create common test data
        self.valid_broker_data = {
            'user_id': self.test_user_id,
            'broker_name': self.test_broker_name,
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret'
        }

    def tearDown(self):
        """Clean up test data."""
        UserBrokerCredential.objects.filter(user_id=self.test_user_id).delete()

    # =========================================================================
    # Tests for register_broker API
    # =========================================================================

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_register_broker_success(self, mock_is_public):
        """Test successful broker registration."""
        # Create request with valid data
        request = self.factory.post(
            self.register_broker_url,
            data=json.dumps(self.valid_broker_data),
            content_type='application/json'
        )
        
        # Define expected response status code
        expected_status_code = status.HTTP_201_CREATED
        
        # Call the view function directly
        response = register_broker(request)
        
        # Validate status code
        self.assertEqual(response.status_code, expected_status_code)
        
        # Parse response content
        content = json.loads(response.content)
        
        # Validate response format
        self.assertEqual(content['status'], 'success')
        self.assertIn('data', content)
        self.assertIn('credential_id', content['data'])
        self.assertEqual(content['data']['broker_name'], self.test_broker_name)
        self.assertTrue(content['data']['is_default'])  # First credential should be default
        
        # Verify database record
        credential = UserBrokerCredential.objects.get(user_id=self.test_user_id)
        self.assertEqual(credential.broker_name, self.test_broker_name)
        self.assertEqual(credential.api_key, 'test_api_key')
        self.assertEqual(credential.api_secret, 'test_api_secret')
        self.assertTrue(credential.is_default)
        self.assertEqual(credential.status, 'active')

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_register_broker_missing_fields(self, mock_is_public):
        """Test register_broker handling of missing required fields."""
        # Create data with missing field
        test_data = self.valid_broker_data.copy()
        del test_data['broker_name']
        
        # Create request
        request = self.factory.post(
            self.register_broker_url,
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        # Define expected response
        expected_status_code = status.HTTP_400_BAD_REQUEST
        expected_error = "Missing required field: broker_name"
        
        # Call the view function
        response = register_broker(request)
        
        # Validate response
        self.assertEqual(response.status_code, expected_status_code)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'error')
        self.assertIn(expected_error, content['error'])

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_register_broker_non_post_method(self, mock_is_public):
        """Test register_broker handling of non-POST method."""
        # Create GET request
        request = self.factory.get(self.register_broker_url)
        
        # Define expected response
        expected_status_code = status.HTTP_405_METHOD_NOT_ALLOWED
        expected_error = "Method not allowed"
        
        # Call the view function
        response = register_broker(request)
        
        # Validate response
        self.assertEqual(response.status_code, expected_status_code)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'error')
        self.assertIn(expected_error, content['error'])

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_register_broker_with_form_data(self, mock_is_public):
        """Test register_broker with form data instead of JSON."""
        # Create form data
        form_data = {
            'user_id': self.test_user_id,
            'broker_name': self.test_broker_name,
            'api_key': 'form_data_api_key',
            'api_secret': 'form_data_api_secret'
        }
        
        # Define expected response
        expected_status_code = status.HTTP_201_CREATED
        
        # Make request
        response = self.client.post(
            self.register_broker_url,
            data=form_data
        )
        
        # Validate response
        self.assertEqual(response.status_code, expected_status_code)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'success')
        
        # Verify in database
        credential = UserBrokerCredential.objects.get(user_id=self.test_user_id, api_key='form_data_api_key')
        self.assertEqual(credential.broker_name, self.test_broker_name)
        self.assertEqual(credential.api_key, 'form_data_api_key')
        self.assertEqual(credential.api_secret, 'form_data_api_secret')



    # =========================================================================
    # Tests for get_user_brokers API
    # =========================================================================

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_get_user_brokers_success(self, mock_is_public):
        """Test successful retrieval of user brokers."""
        # Create test credentials
        cred1 = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='get_test_api_key_1',
            api_secret='get_test_api_secret_1'
        )
        
        cred2 = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='get_test_api_key_2',
            api_secret='get_test_api_secret_2'
        )
        
        # Create request
        request = self.factory.get(
            f"{self.get_user_brokers_url}?user_id={self.test_user_id}"
        )
        
        # Define expected response
        expected_status_code = status.HTTP_200_OK
        expected_broker_count = 2
        
        # Call the view function
        response = get_user_brokers(request)
        
        # Validate response
        self.assertEqual(response.status_code, expected_status_code)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(len(content['data']), expected_broker_count)
        self.assertEqual(content['meta']['count'], expected_broker_count)

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_get_user_brokers_empty_result(self, mock_is_public):
        """Test get_user_brokers with user who has no brokers."""
        # Create a new user ID
        empty_user_id = str(uuid.uuid4())
        
        # Create request
        request = self.factory.get(
            f"{self.get_user_brokers_url}?user_id={empty_user_id}"
        )
        
        # Define expected response
        expected_status_code = status.HTTP_200_OK
        expected_broker_count = 0
        
        # Call the view function
        response = get_user_brokers(request)
        
        # Validate response
        self.assertEqual(response.status_code, expected_status_code)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(len(content['data']), expected_broker_count)
        self.assertEqual(content['meta']['count'], expected_broker_count)

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_get_user_brokers_missing_user_id(self, mock_is_public):
        """Test get_user_brokers with missing user ID."""
        # Create request without user_id
        request = self.factory.get(self.get_user_brokers_url)
        
        # Define expected response
        expected_status_code = status.HTTP_400_BAD_REQUEST
        expected_error = "User ID is required"
        
        # Call the view function
        response = get_user_brokers(request)
        
        # Validate response
        self.assertEqual(response.status_code, expected_status_code)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'error')
        self.assertIn(expected_error, content['error'])

    # =========================================================================
    # Tests for set_default_broker API
    # =========================================================================

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_set_default_broker_success(self, mock_is_public):
        """Test successful setting of default broker."""
        # Create test credentials
        cred1 = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='default_test_api_key_1',
            api_secret='default_test_api_secret_1'
        )
        
        cred2 = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='default_test_api_key_2',
            api_secret='default_test_api_secret_2'
        )
        
        # Verify initial state - first credential should be default
        cred1.refresh_from_db()
        cred2.refresh_from_db()
        self.assertTrue(cred1.is_default)
        self.assertFalse(cred2.is_default)
        
        # Create request with valid data to change default
        request = self.factory.post(
            self.set_default_broker_url,
            data=json.dumps({
                'user_id': self.test_user_id,
                'credential_id': cred2.id  # Set the second credential as default
            }),
            content_type='application/json'
        )
        
        # Define expected response
        expected_status_code = status.HTTP_200_OK
        
        # Call the view function
        response = set_default_broker(request)
        
        # Validate response
        self.assertEqual(response.status_code, expected_status_code)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['data']['credential_id'], cred2.id)
        self.assertTrue(content['data']['is_default'])
        
        # Refresh credentials from database
        cred1.refresh_from_db()
        cred2.refresh_from_db()
        
        # Validate database state
        self.assertFalse(cred1.is_default)
        self.assertTrue(cred2.is_default)

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_set_default_broker_missing_credential_id(self, mock_is_public):
        """Test set_default_broker with missing credential_id."""
        # Create request without credential_id
        request = self.factory.post(
            self.set_default_broker_url,
            data=json.dumps({
                'user_id': self.test_user_id
                # Missing credential_id
            }),
            content_type='application/json'
        )
        
        # Define expected response
        expected_status_code = status.HTTP_400_BAD_REQUEST
        expected_error = "Missing required field: credential_id"
        
        # Call the view function
        response = set_default_broker(request)
        
        # Validate response
        self.assertEqual(response.status_code, expected_status_code)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'error')
        self.assertIn(expected_error, content['error'])

    @patch('ats_gateway.middleware.jwt_auth_middleware.JWTAuthMiddleware.is_public_path', return_value=True)
    def test_set_default_broker_form_data(self, mock_is_public):
        """Test set_default_broker with form data."""
        # Create test credential
        cred = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='form_default_api_key',
            api_secret='form_default_api_secret'
        )
        
        # Create form data
        form_data = {
            'user_id': self.test_user_id,
            'credential_id': cred.id
        }
        
        # Make request
        response = self.client.post(
            self.set_default_broker_url,
            data=form_data
        )
        
        # Validate response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'success')
        
        # Refresh from database
        cred.refresh_from_db()
        
        # Verify database state
        self.assertTrue(cred.is_default) 