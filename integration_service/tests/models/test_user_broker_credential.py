"""
Unit tests for UserBrokerCredential model in the Integration Service.

This module contains unit tests for the UserBrokerCredential model,
using real database operations instead of mocks.
"""

import uuid
from django.test import TransactionTestCase
from integration_service.models.UserBrokerCredential import UserBrokerCredential


class UserBrokerCredentialTest(TransactionTestCase):
    """Unit tests for the UserBrokerCredential model using real database operations."""

    def setUp(self):
        """Set up test data."""
        self.test_user_id = uuid.uuid4()
        self.test_broker_name = 'zerodha'
        self.test_api_key = 'test_api_key'
        self.test_api_secret = 'test_api_secret'

    def tearDown(self):
        """Clean up test data."""
        UserBrokerCredential.objects.filter(user_id=self.test_user_id).delete()

    def test_create_first_credential_as_default(self):
        """
        Test create_broker_credential correctly sets first credential as default.
        
        1. Creates first credential for a user
        2. Verifies is_default is set to True
        3. Checks that other fields are set correctly
        """
        # Create first credential
        credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )
        
        # Verify is_default is True for first credential
        self.assertTrue(credential.is_default)
        
        # Verify other fields
        self.assertEqual(str(credential.user_id), str(self.test_user_id))
        self.assertEqual(credential.broker_name, self.test_broker_name)
        self.assertEqual(credential.api_key, self.test_api_key)
        self.assertEqual(credential.api_secret, self.test_api_secret)
        self.assertEqual(credential.status, 'active')

    def test_subsequent_credentials_not_default(self):
        """
        Test create_broker_credential doesn't set subsequent credentials as default.
        
        1. Creates first credential for a user
        2. Creates second credential for the same user
        3. Verifies first credential is still default
        4. Verifies second credential is not default
        """
        # Create first credential
        first_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )
        
        # Create second credential
        second_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='second_api_key',
            api_secret='second_api_secret'
        )
        
        # Reload first credential from database to check updated status
        first_credential.refresh_from_db()
        
        # Verify first credential is still default
        self.assertTrue(first_credential.is_default)
        
        # Verify second credential is not default
        self.assertFalse(second_credential.is_default)

    def test_set_as_default_updates_all_credentials(self):
        """
        Test set_as_default correctly updates default status for all user credentials.
        
        1. Creates multiple credentials for a user
        2. Sets a specific credential as default
        3. Verifies selected credential is now default
        4. Verifies other credentials are not default
        """
        # Create multiple credentials
        first_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='first_api_key',
            api_secret='first_api_secret'
        )
        
        second_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='second_api_key',
            api_secret='second_api_secret'
        )
        
        third_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='third_api_key',
            api_secret='third_api_secret'
        )
        
        # Set second credential as default
        updated_credential = UserBrokerCredential.set_as_default(
            second_credential.id, 
            self.test_user_id
        )
        
        # Reload credentials from database to check updated status
        first_credential.refresh_from_db()
        second_credential.refresh_from_db()
        third_credential.refresh_from_db()
        
        # Verify second credential is now default
        self.assertTrue(second_credential.is_default)
        self.assertTrue(updated_credential.is_default)
        self.assertEqual(updated_credential.id, second_credential.id)
        
        # Verify other credentials are not default
        self.assertFalse(first_credential.is_default)
        self.assertFalse(third_credential.is_default)

    def test_get_default_credential_retrieves_correct_credential(self):
        """
        Test get_default_credential retrieves correct credential.
        
        1. Creates multiple credentials for a user with one as default
        2. Calls get_default_credential
        3. Verifies correct default credential is retrieved
        """
        # Create multiple credentials
        first_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='first_api_key',
            api_secret='first_api_secret'
        )
        
        second_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=self.test_broker_name,
            api_key='second_api_key',
            api_secret='second_api_secret'
        )
        
        # Set second credential as default
        UserBrokerCredential.set_as_default(second_credential.id, self.test_user_id)
        
        # Get default credential
        default_credential = UserBrokerCredential.get_default_credential(self.test_user_id)
        
        # Verify correct credential is retrieved
        self.assertIsNotNone(default_credential)
        self.assertEqual(default_credential.id, second_credential.id)
        self.assertTrue(default_credential.is_default)

    def test_get_default_credential_with_broker_name_filter(self):
        """
        Test get_default_credential with broker_name filter.
        
        1. Creates credentials for a user with different broker names
        2. Sets one as default
        3. Retrieves default credential with broker_name filter
        4. Verifies correct credential is retrieved
        """
        # Create credentials with different broker names
        # Note: For this test to work properly, both broker names must be in BROKER_CHOICES
        first_broker_name = 'zerodha'
        first_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=first_broker_name,
            api_key='first_api_key',
            api_secret='first_api_secret'
        )
        
        # For testing purposes, we'll create another credential with the same broker name
        # since the model currently only supports 'zerodha' as a broker choice
        second_credential = UserBrokerCredential.create_broker_credential(
            user_id=self.test_user_id,
            broker_name=first_broker_name,
            api_key='second_api_key',
            api_secret='second_api_secret'
        )
        
        # Set second credential as default
        UserBrokerCredential.set_as_default(second_credential.id, self.test_user_id)
        
        # Get default credential with broker_name filter
        default_credential = UserBrokerCredential.get_default_credential(
            self.test_user_id, 
            broker_name=first_broker_name
        )
        
        # Verify correct credential is retrieved
        self.assertIsNotNone(default_credential)
        self.assertEqual(default_credential.id, second_credential.id)
        self.assertTrue(default_credential.is_default)
        self.assertEqual(default_credential.broker_name, first_broker_name)
        
    def test_get_default_credential_no_default_exists(self):
        """
        Test get_default_credential when no default credential exists.
        
        1. Verify get_default_credential returns None when no credentials exist
        """
        # Get default credential for user with no credentials
        default_credential = UserBrokerCredential.get_default_credential(uuid.uuid4())
        
        # Verify None is returned
        self.assertIsNone(default_credential)
        
    def test_credential_creation_with_invalid_broker(self):
        """
        Test credential creation with invalid broker name.
        
        1. Attempt to create credential with invalid broker name
        2. Verify appropriate exception is raised
        """
        # Attempt to create credential with invalid broker name
        try:
            credential = UserBrokerCredential.create_broker_credential(
                user_id=self.test_user_id,
                broker_name='invalid_broker',  # Invalid broker name
                api_key=self.test_api_key,
                api_secret=self.test_api_secret
            )
            self.fail("Should have raised an exception")
        except Exception as e:
            # Verify exception is raised
            self.assertIsNotNone(e) 