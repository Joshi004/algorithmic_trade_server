# Authentication System Tests

This directory contains test suites for the ATS Gateway authentication system. The tests cover various aspects of the authentication flow, including JWT token generation/validation, login/registration API endpoints, and the middleware that enforces token requirements.

## Test Approach

All tests in this project use Django's TestCase framework, which provides robust testing capabilities integrated with the database. This approach ensures that tests are:

- Fully integrated with Django's test infrastructure
- Able to use the test database for proper database testing
- Consistent in structure and execution
- Properly isolated between test runs

## Test Organization

The tests are organized into the following files:

1. **test_jwt_utils.py**: Unit tests for JWT token utilities (generation, decoding, verification)
2. **test_login_serializer.py**: Unit tests for the login serializer (credential validation) 
3. **test_auth_view.py**: Unit tests for authentication views (login API endpoint)
4. **test_register_api.py**: Unit tests for user registration API (validation and user creation)
5. **test_jwt_middleware.py**: Unit tests for the JWT authentication middleware (token enforcement)
6. **test_functional_auth.py**: Functional tests for end-to-end authentication flows

## Running Tests with Test Database

The project is configured to run tests using a dedicated test database. There are two ways to run tests:

### 1. Using the Docker Test Script

The easiest way is to use the provided script which will run tests inside the Docker container:

```bash
# Run all ATS Gateway tests
./docker_run_tests.sh ats_gateway.tests

# Run a specific test file
./docker_run_tests.sh ats_gateway.tests.test_jwt_utils

# Run a specific test case
./docker_run_tests.sh ats_gateway.tests.test_auth_view.AuthViewTestCase

# Run tests with options (e.g., keep the test database between runs)
./docker_run_tests.sh ats_gateway.tests --keepdb
```

### 2. From Inside the Container

You can also execute tests directly inside the container with the test settings:

```bash
# Execute tests within the running Docker container
docker exec -it ats-django-app bash -c "DJANGO_SETTINGS_MODULE=ats_base.test_settings python manage.py test ats_gateway.tests"
```

## Database Setup for Tests

Tests use a dedicated test database (`test_ats_db`) that's configured in:

1. `mysql-init/01-test-db-init.sql` - Creates and grants permissions for the test database
2. `ats_base/test_settings.py` - Django settings for test environment
3. Docker configuration with proper environment variables

## Test Coverage

The tests cover:

- Unit testing of all authentication components
- Token generation, validation, and expiration
- Login/registration API endpoints
- Protection of endpoints by token type
- Error scenarios and edge cases
- Complete end-to-end authentication workflows

## Test Data

The tests use a combination of:
- Actual database tables (using the test database)
- Fixtures and model instances for test data
- Valid/invalid credentials
- Active/inactive user accounts
- Valid/expired/invalid tokens
- Different token types (long-lived vs. short-lived)

## Best Practices for Writing Tests

When adding new tests, follow these guidelines:
1. Add detailed docstrings at the file, class, and method levels
2. Use descriptive test method names prefixed with `test_`
   - Example: `test_login_with_valid_credentials_returns_tokens`
   - Example: `test_expired_token_fails_validation`
3. Add proper setup code in the `setUp` method
4. Follow the pattern of arrange-act-assert in test methods:
   ```python
   # Arrange
   test_user = User.objects.create(...)
   
   # Act
   response = self.client.post(self.login_url, data)
   
   # Assert
   self.assertEqual(response.status_code, 200)
   ```
5. Use Django's TestCase for database-dependent tests or SimpleTestCase for others
6. Clean up after your tests to maintain independence between tests
7. Group related tests logically within a TestCase class
8. Keep tests focused on testing one specific behavior
