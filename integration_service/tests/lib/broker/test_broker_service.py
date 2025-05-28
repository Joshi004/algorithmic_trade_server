"""
Unit tests for BrokerService class in the Integration Service.

This module contains unit tests for the BrokerService class,
using real database operations with raw SQL for data verification.
"""

import uuid
import os
from django.test import TransactionTestCase
from integration_service.models.UserBrokerCredential import UserBrokerCredential
from integration_service.lib.broker.broker_service import BrokerService


class BrokerServiceTest(TransactionTestCase):
    """Unit tests for the BrokerService class using real database operations."""

    def setUp(self):
        """Set up test data and service instance."""
        # Initialize broker service
        self.broker_service = BrokerService()
        
        # Generate test data values
        self.test_user_id = str(uuid.uuid4())
        self.test_broker_name = 'zerodha'
        self.test_api_key = 'test_api_key'
        self.test_api_secret = 'test_api_secret'
        
        # Set required environment variables
        if not os.environ.get('BROKER_ENCRYPTION_SECRET'):
            os.environ['BROKER_ENCRYPTION_SECRET'] = 'test_encryption_secret'

    def tearDown(self):
        """Clean up test data using raw SQL."""
        # Delete using the ORM to handle any UUID conversions
        UserBrokerCredential.objects.filter(user_id=self.test_user_id).delete()

    def test_register_broker_creates_credential(self):
        """Test register_broker method correctly creates credential."""
        # Define expected response format
        expected_response = {
            'status': 'success',
            'data': {
                'broker_name': self.test_broker_name,
                'is_default': True,
                'status': 'active'
            }
        }
        
        # Call the register_broker method
        actual_response = self.broker_service.register_broker(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )
        
        # Check for successful response
        self.assertEqual(actual_response['status'], 'success', 
                         f"Failed to register broker: {actual_response.get('error', 'Unknown error')}")
        
        # Get credential from database to verify using ORM
        credential = UserBrokerCredential.objects.get(user_id=self.test_user_id)
        
        # Verify credential fields
        self.assertEqual(credential.broker_name, self.test_broker_name)
        self.assertEqual(credential.api_key, self.test_api_key)
        self.assertEqual(credential.api_secret, self.test_api_secret)
        self.assertTrue(credential.is_default)
        self.assertEqual(credential.status, 'active')
        
        # Update expected response with actual credential ID
        expected_response['data']['credential_id'] = credential.id
        
        # Verify response matches expected format and content
        self.assertEqual(actual_response['status'], expected_response['status'])
        self.assertEqual(actual_response['data']['credential_id'], expected_response['data']['credential_id'])
        self.assertEqual(actual_response['data']['broker_name'], expected_response['data']['broker_name'])
        self.assertEqual(actual_response['data']['is_default'], expected_response['data']['is_default'])
        self.assertEqual(actual_response['data']['status'], expected_response['data']['status'])

    def test_get_user_brokers_returns_correct_list(self):
        """Test get_user_brokers method returns correct broker list."""
        # Create test credentials using the service
        response1 = self.broker_service.register_broker(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='test_api_key_1',
            api_secret='test_api_secret_1'
        )
        self.assertEqual(response1['status'], 'success', 
                         f"Failed to register first broker: {response1.get('error', 'Unknown error')}")
        
        response2 = self.broker_service.register_broker(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='test_api_key_2',
            api_secret='test_api_secret_2'
        )
        self.assertEqual(response2['status'], 'success', 
                         f"Failed to register second broker: {response2.get('error', 'Unknown error')}")
        
        # Get credential IDs from responses
        credential1_id = response1['data']['credential_id']
        credential2_id = response2['data']['credential_id']
        
        # Call the get_user_brokers method
        actual_response = self.broker_service.get_user_brokers(self.test_user_id)
        
        # Verify response format and content
        self.assertEqual(actual_response['status'], 'success')
        self.assertEqual(len(actual_response['data']), 2)
        self.assertEqual(actual_response['meta']['count'], 2)
        
        # Get credential IDs from response
        result_ids = [item['credential_id'] for item in actual_response['data']]
        self.assertIn(credential1_id, result_ids)
        self.assertIn(credential2_id, result_ids)
        
        # Find each credential in response
        cred1_result = next(item for item in actual_response['data'] if item['credential_id'] == credential1_id)
        cred2_result = next(item for item in actual_response['data'] if item['credential_id'] == credential2_id)
        
        # Verify first credential data
        self.assertEqual(cred1_result['broker_name'], self.test_broker_name)
        self.assertEqual(cred1_result['is_default'], True)
        self.assertEqual(cred1_result['status'], 'active')
        
        # Verify second credential data
        self.assertEqual(cred2_result['broker_name'], self.test_broker_name)
        self.assertEqual(cred2_result['is_default'], False)
        self.assertEqual(cred2_result['status'], 'active')

    def test_set_default_broker_updates_default_status(self):
        """Test set_default_broker method correctly updates default status."""
        # Create test credentials using the service
        response1 = self.broker_service.register_broker(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='test_api_key_1',
            api_secret='test_api_secret_1'
        )
        self.assertEqual(response1['status'], 'success', 
                         f"Failed to register first broker: {response1.get('error', 'Unknown error')}")
        
        response2 = self.broker_service.register_broker(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='test_api_key_2',
            api_secret='test_api_secret_2'
        )
        self.assertEqual(response2['status'], 'success', 
                         f"Failed to register second broker: {response2.get('error', 'Unknown error')}")
        
        # Get credential IDs from responses
        credential1_id = response1['data']['credential_id']
        credential2_id = response2['data']['credential_id']
        
        # Define expected response
        expected_response = {
            'status': 'success',
            'data': {
                'credential_id': credential2_id,
                'broker_name': self.test_broker_name,
                'is_default': True
            }
        }
        
        # Call the set_default_broker method to change default
        actual_response = self.broker_service.set_default_broker(
            user_id=self.test_user_id,
            credential_id=credential2_id
        )
        
        # Verify response is successful
        self.assertEqual(actual_response['status'], 'success', 
                         f"Failed to set default broker: {actual_response.get('error', 'Unknown error')}")
        
        # Refresh credential objects from database
        credentials = UserBrokerCredential.objects.filter(
            user_id=self.test_user_id
        ).order_by('id')
        
        # Verify there are two credentials
        self.assertEqual(len(credentials), 2, "Expected 2 credential records")
        
        # Verify the default status was updated correctly
        self.assertFalse(credentials[0].is_default, "First credential should not be default")
        self.assertTrue(credentials[1].is_default, "Second credential should be default")
        
        # Verify actual response matches expected format and content
        self.assertEqual(actual_response['status'], expected_response['status'])
        self.assertEqual(actual_response['data']['credential_id'], expected_response['data']['credential_id'])
        self.assertEqual(actual_response['data']['broker_name'], expected_response['data']['broker_name'])
        self.assertEqual(actual_response['data']['is_default'], expected_response['data']['is_default'])

    def test_register_broker_exception_handling(self):
        """Test register_broker exception handling with invalid broker_name."""
        # Call register_broker with invalid broker_name
        actual_response = self.broker_service.register_broker(
            user_id=self.test_user_id,
            broker_name='invalid_broker',  # Invalid broker name not in BROKER_CHOICES
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )
        
        # Verify error response
        self.assertEqual(actual_response['status'], 'error')
        self.assertIn('error', actual_response)
        self.assertIsNotNone(actual_response['error'])
        
        # Verify no credential was created
        self.assertEqual(
            UserBrokerCredential.objects.filter(user_id=self.test_user_id).count(), 
            0, 
            "Expected no credential records"
        )

    def test_get_user_brokers_empty_result(self):
        """Test get_user_brokers returns empty list for user with no brokers."""
        # Define a user ID with no credentials
        empty_user_id = str(uuid.uuid4())
        
        # Define expected response
        expected_response = {
            'status': 'success',
            'data': [],
            'meta': {
                'count': 0
            }
        }
        
        # Call get_user_brokers for user with no credentials
        actual_response = self.broker_service.get_user_brokers(empty_user_id)
        
        # Verify actual response matches expected format and content
        self.assertEqual(actual_response['status'], expected_response['status'])
        self.assertEqual(actual_response['data'], expected_response['data'])
        self.assertEqual(actual_response['meta']['count'], expected_response['meta']['count'])

    def test_set_default_broker_nonexistent_credential(self):
        """Test set_default_broker with non-existent credential ID."""
        # Call set_default_broker with non-existent credential ID
        actual_response = self.broker_service.set_default_broker(
            user_id=self.test_user_id,
            credential_id=99999  # Non-existent ID
        )
        
        # Verify error response
        self.assertEqual(actual_response['status'], 'error')
        self.assertIn('error', actual_response)
        self.assertIsNotNone(actual_response['error'])

    def test_encryption_decryption_methods(self):
        """Test encryption/decryption methods work correctly."""
        # Define test secret
        test_secret = 'test_api_secret'
        
        # Encrypt the secret
        encrypted = self.broker_service._encrypt_secret(test_secret)
        
        # Verify encrypted value is different from original
        self.assertNotEqual(encrypted, test_secret)
        
        # Decrypt the secret
        decrypted = self.broker_service._decrypt_secret(encrypted)
        
        # Verify decrypted value matches original
        self.assertEqual(decrypted, test_secret) 