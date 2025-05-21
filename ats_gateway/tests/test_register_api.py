"""
Test module for registration API in the ATS Gateway.

This module contains unit tests for the user registration endpoint,
focusing on validation of user inputs, error handling, and successful user creation.
The tests verify API behavior, response formats, field validation, and database creation.

These tests use Django's test client to simulate HTTP requests and verify the API responses.
"""

import json
import uuid
import re
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from ..models.User import User


class RegisterAPITestCase(TestCase):
    """Test cases for the registration API endpoint.
    
    This test case validates the behavior of the user registration endpoint, focusing on:
    - Successful user registration
    - Email validation
    - Password validation rules
    - Duplicate email handling
    - Error responses
    - HTTP method validation
    
    The tests use Django's test client to make requests to the API endpoint
    and verify the responses and database state.
    """

    def setUp(self):
        """Set up test case data.
        
        Initializes the test client, defines API endpoint URL, and creates
        test user data to be used in registration tests.
        """
        self.client = Client()
        self.register_url = reverse('register')
        
        # Valid test data
        self.valid_user_data = {
            'email': 'test@example.com',
            'password': 'Password123!'
        }
        
        # Data for testing duplicate registration
        self.existing_user_email = 'existing@example.com'
        User.objects.create_user(
            email=self.existing_user_email,
            password='ExistingPass123!'
        )

    def test_registration_success(self):
        """Test successful user registration.
        
        Verifies that:
        1. The API returns a 201 Created status code on successful registration
        2. The response contains the user's email and public_id
        3. The user is successfully created in the database
        4. The user's password is properly hashed
        """
        # Make registration request
        response = self.client.post(
            self.register_url,
            data=json.dumps(self.valid_user_data),
            content_type='application/json'
        )
        
        # Assert response status and content
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['email'], self.valid_user_data['email'])
        self.assertIn('public_id', response.data)
        
        # Get the public_id and validate it
        public_id = response.data['public_id']
        
        # Validate that it's a valid UUID value based on type
        if isinstance(public_id, str):
            # If it's a string, validate with regex pattern
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            self.assertTrue(
                uuid_pattern.match(public_id) is not None,
                f"public_id '{public_id}' is not a valid UUID string format"
            )
        elif isinstance(public_id, uuid.UUID):
            # If it's a UUID object, it's already valid (no further validation needed)
            pass
        else:
            # For any other type, try to convert to string and validate
            str_public_id = str(public_id)
            try:
                # Try to construct a UUID from the string
                uuid.UUID(str_public_id)
            except (ValueError, AttributeError, TypeError):
                self.fail(f"public_id '{public_id}' is not a valid UUID or UUID string")
        
        # Verify user creation in database
        self.assertTrue(
            User.objects.filter(email=self.valid_user_data['email']).exists(),
            "User was not created in the database"
        )
        
        # Get the created user
        user = User.objects.get(email=self.valid_user_data['email'])
        
        # Verify the user is active by default
        self.assertTrue(user.is_active)
        
        # Verify password is hashed (not stored in plaintext)
        self.assertNotEqual(user.password, self.valid_user_data['password'])
        self.assertTrue(user.password.startswith('$2b$'), "Password doesn't appear to be hashed with bcrypt")

    def test_registration_invalid_email(self):
        """Test registration with an invalid email format.
        
        Verifies that:
        1. The API returns a 400 Bad Request status code for invalid email
        2. The response contains appropriate error messages
        3. No user is created in the database
        """
        # Invalid email formats to test
        invalid_emails = [
            'not_an_email',
            'missing@tld',
            '@missing_username.com',
            'spaces in@email.com',
            'unicode☺@example.com'
        ]
        
        for invalid_email in invalid_emails:
            data = {
                'email': invalid_email,
                'password': 'Password123!'
            }
            
            # Make registration request
            response = self.client.post(
                self.register_url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            # Assert response
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('email', response.data)
            
            # Verify no user is created
            self.assertFalse(
                User.objects.filter(email=invalid_email).exists(),
                f"User with invalid email '{invalid_email}' was created"
            )

    def test_registration_password_too_short(self):
        """Test registration with a password that is too short.
        
        Verifies that:
        1. The API returns a 400 Bad Request status code for short passwords
        2. The response contains error message about password length
        3. No user is created in the database
        """
        data = {
            'email': 'valid@example.com',
            'password': 'Short1!'  # 7 characters, minimum is 8
        }
        
        # Make registration request
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertTrue(
            any('8 characters' in str(error) for error in response.data['password']),
            "Error message doesn't mention password length requirement"
        )
        
        # Verify no user is created
        self.assertFalse(
            User.objects.filter(email=data['email']).exists(),
            "User with short password was created"
        )

    def test_registration_password_no_uppercase(self):
        """Test registration with a password missing an uppercase letter.
        
        Verifies that:
        1. The API returns a 400 Bad Request status code for passwords without uppercase
        2. The response contains error message about uppercase requirement
        3. No user is created in the database
        """
        data = {
            'email': 'valid@example.com',
            'password': 'password123!'  # No uppercase
        }
        
        # Make registration request
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertTrue(
            any('uppercase' in str(error) for error in response.data['password']),
            "Error message doesn't mention uppercase requirement"
        )
        
        # Verify no user is created
        self.assertFalse(
            User.objects.filter(email=data['email']).exists(),
            "User with password missing uppercase was created"
        )

    def test_registration_password_no_digit(self):
        """Test registration with a password missing a numeric digit.
        
        Verifies that:
        1. The API returns a 400 Bad Request status code for passwords without digits
        2. The response contains error message about digit requirement
        3. No user is created in the database
        """
        data = {
            'email': 'valid@example.com',
            'password': 'Password!'  # No digit
        }
        
        # Make registration request
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertTrue(
            any('digit' in str(error) for error in response.data['password']),
            "Error message doesn't mention digit requirement"
        )
        
        # Verify no user is created
        self.assertFalse(
            User.objects.filter(email=data['email']).exists(),
            "User with password missing digit was created"
        )

    def test_registration_password_no_special_char(self):
        """Test registration with a password missing a special character.
        
        Verifies that:
        1. The API returns a 400 Bad Request status code for passwords without special chars
        2. The response contains error message about special character requirement
        3. No user is created in the database
        """
        data = {
            'email': 'valid@example.com',
            'password': 'Password123'  # No special character
        }
        
        # Make registration request
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertTrue(
            any('special character' in str(error) for error in response.data['password']),
            "Error message doesn't mention special character requirement"
        )
        
        # Verify no user is created
        self.assertFalse(
            User.objects.filter(email=data['email']).exists(),
            "User with password missing special character was created"
        )

    def test_registration_missing_fields(self):
        """Test registration with missing required fields.
        
        Verifies that:
        1. The API returns a 400 Bad Request status code when required fields are missing
        2. The response contains appropriate error messages for each missing field
        3. No user is created in the database
        """
        # Test missing email
        missing_email = {
            'password': 'Password123!'
        }
        response1 = self.client.post(
            self.register_url,
            data=json.dumps(missing_email),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response1.data)
        
        # Test missing password
        missing_password = {
            'email': 'valid@example.com'
        }
        response2 = self.client.post(
            self.register_url,
            data=json.dumps(missing_password),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response2.data)
        
        # Test empty request
        empty_request = {}
        response3 = self.client.post(
            self.register_url,
            data=json.dumps(empty_request),
            content_type='application/json'
        )
        self.assertEqual(response3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response3.data)
        self.assertIn('password', response3.data)

    def test_registration_duplicate_email(self):
        """Test registration with an email that already exists.
        
        Verifies that:
        1. The API returns a 400 Bad Request status code for duplicate email
        2. The response contains error message about email uniqueness
        3. No additional user is created in the database
        """
        # Create data with existing email
        data = {
            'email': self.existing_user_email,
            'password': 'Password123!'
        }
        
        # Make registration request
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        
        # Check there's still only one user with this email
        self.assertEqual(
            User.objects.filter(email=self.existing_user_email).count(),
            1,
            "Multiple users with the same email were created"
        )

    def test_registration_incorrect_method(self):
        """Test registration with incorrect HTTP method.
        
        Verifies that:
        1. The registration endpoint only accepts POST requests
        2. GET, PUT, PATCH, DELETE requests are rejected with 405 Method Not Allowed
        """
        # Test with GET method (should be POST)
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test with PUT method
        response = self.client.put(
            self.register_url,
            data=json.dumps(self.valid_user_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test with PATCH method
        response = self.client.patch(
            self.register_url,
            data=json.dumps(self.valid_user_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test with DELETE method
        response = self.client.delete(self.register_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
