"""
Test module for LoginSerializer in the ATS Gateway.

This module contains unit tests for the login serializer which validates user credentials
during the login process. The tests cover validation of email/password combinations,
handling of inactive accounts, and validation of input format and required fields.

The tests use mocking to simulate database interactions and bcrypt for password
verification while testing different login scenarios.
"""

import uuid
import bcrypt
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from ..serializers.LoginSerializer import LoginSerializer


class LoginSerializerTestCase(TestCase):
    """Test cases for the LoginSerializer.
    
    This test case validates the LoginSerializer's functionality for:
    - Successful credential validation
    - Handling of nonexistent users
    - Validation of passwords using bcrypt
    - Rejection of inactive user accounts
    - Input field validation
    
    The tests mock the User model and database interactions to focus on
    testing the serializer's logic in isolation.
    """

    def setUp(self):
        """Set up test data.
        
        Creates test credentials with valid email/password and a mock user object
        with a bcrypt-hashed password for testing password validation.
        """
        self.valid_email = "test@example.com"
        self.valid_password = "Password123!"
        
        # Create mock user with hashed password
        self.user_public_id = uuid.uuid4()
        self.hashed_password = bcrypt.hashpw(self.valid_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Mock attributes
        self.mock_user = MagicMock()
        self.mock_user.email = self.valid_email
        self.mock_user.password = self.hashed_password
        self.mock_user.public_id = self.user_public_id
        self.mock_user.is_active = True

    @patch('django.contrib.auth.authenticate')
    @patch('ats_gateway.serializers.LoginSerializer.User.objects.get')
    def test_valid_login(self, mock_get, mock_authenticate):
        """Test login with valid credentials.
        
        Verifies that the serializer:
        1. Successfully validates when given correct credentials
        2. Returns the correct user information in validated_data
        3. Properly retrieves the user from the database
        
        Uses mocking to simulate the database lookup.
        """
        # Set up mock response
        mock_get.return_value = self.mock_user
        
        # Create serializer with valid data
        serializer = LoginSerializer(data={
            'email': self.valid_email,
            'password': self.valid_password
        })
        
        # Validate and check result
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'], self.valid_email)
        self.assertEqual(serializer.validated_data['public_id'], self.user_public_id)

    @patch('ats_gateway.serializers.LoginSerializer.User.objects.get')
    def test_nonexistent_user(self, mock_get):
        """Test login with non-existent user.
        
        Verifies that the serializer:
        1. Correctly handles attempts to log in with an email that doesn't exist
        2. Returns appropriate validation errors
        3. Maintains security by not revealing whether the email or password was incorrect
        
        Uses mocking to simulate a database lookup that raises ObjectDoesNotExist.
        """
        # Set up mock to raise ObjectDoesNotExist
        mock_get.side_effect = ObjectDoesNotExist()
        
        # Create serializer with non-existent email
        serializer = LoginSerializer(data={
            'email': 'nonexistent@example.com',
            'password': self.valid_password
        })
        
        # Validation should fail
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn('Invalid email or password', str(serializer.errors['non_field_errors']))

    @patch('ats_gateway.serializers.LoginSerializer.User.objects.get')
    def test_invalid_password(self, mock_get):
        """Test login with invalid password.
        
        Verifies that the serializer:
        1. Rejects login attempts with incorrect passwords
        2. Uses bcrypt to correctly validate passwords
        3. Returns appropriate validation errors
        4. Maintains security by not revealing whether the email or password was incorrect
        
        Mocks the user object but uses actual bcrypt password checking.
        """
        # Set up mock response
        mock_get.return_value = self.mock_user
        
        # Create serializer with invalid password
        serializer = LoginSerializer(data={
            'email': self.valid_email,
            'password': 'WrongPassword123!'
        })
        
        # Validation should fail
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn('Invalid email or password', str(serializer.errors['non_field_errors']))

    @patch('ats_gateway.serializers.LoginSerializer.User.objects.get')
    def test_inactive_user(self, mock_get):
        """Test login with inactive user account.
        
        Verifies that the serializer:
        1. Rejects login attempts for inactive user accounts
        2. Checks the is_active flag on the user model
        3. Returns appropriate validation errors
        4. Maintains security by not revealing that the account is inactive
        
        Tests the serializer's handling of the is_active flag on the user model.
        """
        # Create an inactive mock user
        inactive_user = MagicMock()
        inactive_user.email = self.valid_email
        inactive_user.password = self.hashed_password
        inactive_user.is_active = False
        
        # Set up mock response
        mock_get.return_value = inactive_user
        
        # Create serializer with valid credentials but inactive account
        serializer = LoginSerializer(data={
            'email': self.valid_email,
            'password': self.valid_password
        })
        
        # Validation should fail
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn('Invalid email or password', str(serializer.errors['non_field_errors']))

    def test_missing_fields(self):
        """Test validation with missing fields.
        
        Verifies that the serializer:
        1. Rejects requests missing the email field
        2. Rejects requests missing the password field
        3. Rejects empty requests
        4. Returns appropriate field-specific validation errors
        
        Ensures required fields are properly enforced by the serializer.
        """
        # Test with missing email
        serializer1 = LoginSerializer(data={'password': self.valid_password})
        self.assertFalse(serializer1.is_valid())
        self.assertIn('email', serializer1.errors)
        
        # Test with missing password
        serializer2 = LoginSerializer(data={'email': self.valid_email})
        self.assertFalse(serializer2.is_valid())
        self.assertIn('password', serializer2.errors)
        
        # Test with empty data
        serializer3 = LoginSerializer(data={})
        self.assertFalse(serializer3.is_valid())
        self.assertIn('email', serializer3.errors)
        self.assertIn('password', serializer3.errors)

    def test_invalid_email_format(self):
        """Test validation with invalid email format.
        
        Verifies that the serializer:
        1. Validates the format of the email field
        2. Rejects malformed email addresses
        3. Returns appropriate field-specific validation errors
        
        Tests the email field validation logic in the serializer.
        """
        # Test with invalid email format
        serializer = LoginSerializer(data={
            'email': 'not-an-email',
            'password': self.valid_password
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
