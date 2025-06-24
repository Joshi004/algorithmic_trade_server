# ATS Testing Infrastructure

## Overview

This directory contains the testing infrastructure for the ATS (Algorithmic Trading Server) application. The tests are designed to run inside Docker containers with real database interactions and minimal mocking.

## Quick Start (Docker Container Mode)

### Prerequisites

1. **Start Docker Containers**:
   ```bash
   docker-compose up -d
   ```

2. **Verify Containers are Running**:
   ```bash
   docker ps
   ```
   You should see these containers running:
   - `ats-mysql-db`
   - `ats-django-app`
   - `ats-redis-server`
   - `ats-scanning-service`
   - `ats-session-monitor`

### Running Tests

The testing infrastructure now runs inside Docker containers for consistency and isolation.

**Basic Usage:**
```bash
# Run all tests with coverage
./run_tests.sh

# Run tests verbosely
./run_tests.sh -v

# Run specific test pattern
./run_tests.sh -p "test_get_login"

# Run integration tests only
./run_tests.sh -m integration

# Run without coverage (faster)
./run_tests.sh -c
```

## Test Architecture

### Container-Based Testing

- **Test Execution**: Tests run inside the `ats-django-app` container
- **Test Database**: Dedicated `ats_db_test` database in the `ats-mysql-db` container
- **Test Isolation**: Each test gets a clean database state
- **Real Interactions**: Tests use actual database and Redis operations

### Test Data Management

Tests use ASCII table format for readable test data:

```python
def test_example(self, table_data_manager):
    # Setup test data with clear visibility
    credentials_data = """
    +--------------------------------------+-------------+------------------+--------+
    | user_id                              | broker_name | api_key          | status |
    +--------------------------------------+-------------+------------------+--------+
    | 12345678-1234-1234-1234-123456789012 | zerodha     | test_active_key  | active |
    +--------------------------------------+-------------+------------------+--------+
    """
    
    table_data_manager.insert_table_data('user_broker_credentials', credentials_data)
    
    # Test logic here...
```

## Test Organization

```
tests/
├── README.md                    # This documentation
├── settings.py                  # Test-specific Django settings
├── conftest.py                  # Pytest fixtures and configuration
├── utils/
│   └── table_data_manager.py    # ASCII table data management utility
└── integration_service/
    └── test_kite_auth_view.py    # Tests for kite_auth_view
```

## Configuration Files

### `pytest.ini`
- Test discovery and markers
- Coverage configuration (80% threshold)
- Test execution options

### `tests/settings.py`
- Container-aware database configuration
- Test-specific overrides
- Optimized for test performance

### `tests/conftest.py`
- Shared fixtures for all tests
- Database and authentication utilities
- Test data management tools

## Running Tests - Step by Step

1. **Start Infrastructure**:
   ```bash
   docker-compose up -d
   ```

2. **Run Tests**:
   ```bash
   ./run_tests.sh
   ```

3. **View Results**:
   - Test results appear in terminal
   - Coverage report: `htmlcov/index.html`
   - Test database: `ats_db_test` (automatically managed)

## Test Philosophy

- **Real Database Operations**: No mocking of database interactions
- **Minimal External Mocking**: Only mock external APIs (KiteConnect, etc.)
- **Clear Test Data**: ASCII table format for easy visibility
- **Simple Input-Output**: Setup → Input → Process → Compare → Cleanup
- **Container Isolation**: Tests run in clean, consistent environment

## Troubleshooting

### Container Issues
```bash
# Check container status
docker ps

# Restart containers
docker-compose restart

# View container logs
docker logs ats-django-app
docker logs ats-mysql-db
```

### Database Issues
```bash
# Check test database
docker exec ats-mysql-db mysql -u ats_user -pats_password -e "SHOW DATABASES;"

# Recreate test database
docker exec ats-mysql-db mysql -u root -prootpassword -e "DROP DATABASE IF EXISTS ats_db_test; CREATE DATABASE ats_db_test;"
```

### Test Debugging
```bash
# Run tests verbosely with no coverage
./run_tests.sh -v -c

# Run specific test
./run_tests.sh -p "test_get_login_url_with_active_credentials"

# Run tests with minimal output
./run_tests.sh --disable-warnings
```

## Development Workflow

1. **Write Test**: Create test using ASCII table data format
2. **Run Single Test**: `./run_tests.sh -p "your_test_name"`
3. **Debug if Needed**: Add verbose flag `-v`
4. **Run Full Suite**: `./run_tests.sh` before committing
5. **Check Coverage**: Open `htmlcov/index.html`

## Advanced Usage

### Custom Test Database
```bash
./run_tests.sh -d "custom_test_db_name"
```

### Parallel Testing
```bash
./run_tests.sh -w 4  # Use 4 parallel workers
```

### Coverage Threshold
```bash
./run_tests.sh -t 85  # Require 85% coverage
```

## Example Test Structure

```python
def test_example_feature(self, authenticated_request_factory, table_data_manager):
    """
    Test: Description of what is being tested
    Input: Description of input
    Expected Output: Description of expected result
    """
    # Setup test data
    table_data_manager.clear_table_completely('table_name')
    
    test_data = """
    +----------+----------+
    | column1  | column2  |
    +----------+----------+
    | value1   | value2   |
    +----------+----------+
    """
    
    table_data_manager.insert_table_data('table_name', test_data)
    
    # Input
    request = authenticated_request_factory.authenticated_get('/endpoint', user_id)
    
    # Expected output
    expected_response = {'status': 'success'}
    
    # Process
    response = view_function(request)
    
    # Compare output
    assert response.status_code == 200
    assert json.loads(response.content) == expected_response
```

## Features

- **pytest with pytest-django** - Modern testing framework with Django integration
- **Real Database Interactions** - Tests use actual database operations for realistic testing
- **Test Isolation** - Each test starts with a clean database state
- **Data Snapshot Utilities** - Tools for handling SQL data and database state management
- **Factory Pattern** - Realistic test data generation using factory_boy
- **Minimal Mocking** - Only external APIs are mocked, internal logic is tested realistically
- **Comprehensive Coverage** - Integration tests verify complete request/response flows

## Directory Structure

```
tests/
├── __init__.py                     # Tests package
├── conftest.py                     # pytest configuration and fixtures
├── settings.py                     # Django test settings
├── README_ASCII_TABLES.md          # ASCII table format guide (recommended approach)
├── README.md                       # This file
├── utils/
│   ├── __init__.py
│   └── data_snapshot.py           # Data snapshot utilities
└── integration_service/
    ├── __init__.py
    └── test_kite_auth_views.py     # Integration tests for Kite auth views
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Install testing dependencies
pip install -r requirements.txt
```

### 2. Database Setup

Create a dedicated test database:

```sql
-- MySQL setup
CREATE DATABASE ats_db_test;
GRANT ALL PRIVILEGES ON ats_db_test.* TO 'your_user'@'localhost';
```

### 3. Environment Variables

Set up test-specific environment variables:

```bash
# Test database configuration
export TEST_DATABASE_NAME=ats_db_test
export TEST_DATABASE_USER=your_user
export TEST_DATABASE_PASSWORD=your_password
export TEST_DATABASE_HOST=localhost
export TEST_DATABASE_PORT=3306

# Use different Redis DB for tests
export TEST_REDIS_DB=1
```

### 4. Run Migrations

```bash
# Create test database tables
python manage.py migrate --settings=tests.settings
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/integration_service/test_kite_auth_views.py

# Run specific test class
pytest tests/integration_service/test_kite_auth_views.py::TestGetLoginUrlView

# Run specific test method
pytest tests/integration_service/test_kite_auth_views.py::TestGetLoginUrlView::test_get_login_url_with_active_credential_success
```

### Test Categories

Tests are organized using markers:

```bash
# Run only integration tests
pytest -m integration

# Run only database-dependent tests
pytest -m requires_db

# Run only unit tests (fast)
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Run tests that require broker credentials
pytest -m requires_broker
```

### Coverage Reports

```bash
# Run tests with coverage
pytest --cov=.

# Generate HTML coverage report
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
pytest -n auto

# Run tests in parallel with specific number of workers
pytest -n 4
```

## Test Writing Guide

### Basic Test Structure

```python
import pytest
import uuid

@pytest.mark.integration
@pytest.mark.requires_db
class TestYourView:
    def test_your_scenario(self, authenticated_request_factory, table_data_manager):
        # 1. Setup test data using readable ASCII table
        table_data_manager.clear_table_completely('user_broker_credentials')
        user_id = "4820c5b9-2843-468c-a4fb-e4e037a77281"
        
        credentials_table = f"""
        +--------------------------------------+-------------+------------------+--------+
        | user_id                              | broker_name | api_key          | status |
        +--------------------------------------+-------------+------------------+--------+
        | {user_id}                            | zerodha     | test_api_key_123 | active |
        +--------------------------------------+-------------+------------------+--------+
        """
        
        # 2. Insert data (with manual cleanup pattern for complete control)
        table_data_manager.insert_table_data('user_broker_credentials', credentials_table)
        
        # 3. Execute test
        request = authenticated_request_factory.authenticated_get('/your-endpoint', uuid.UUID(user_id))
        response = your_view_function(request)
        
        # 4. Verify results
        assert response.status_code == 200
        
        # 5. Manual cleanup ensures complete control over test data
```

### Using ASCII Tables (Recommended)

```python
# Create readable test data using ASCII tables
credentials_table = """
+--------------------------------------+-------------+------------------+--------+
| user_id                              | broker_name | api_key          | status |
+--------------------------------------+-------------+------------------+--------+
| 4820c5b9-2843-468c-a4fb-e4e037a77281 | zerodha     | test_key_123     | active |
| 5730d6c1-3954-579d-b5ec-f5f148b88392 | zerodha     | test_key_456     | pending|
+--------------------------------------+-------------+------------------+--------+
"""

# Clear table and insert data with manual cleanup for complete control
table_data_manager.clear_table_completely('user_broker_credentials')
table_data_manager.insert_table_data('user_broker_credentials', credentials_table)

# For complex scenarios with multiple tables
table_data_manager.clear_table_completely('users')
table_data_manager.clear_table_completely('user_broker_credentials')
tables_data = {
    'users': users_ascii_table,
    'user_broker_credentials': credentials_ascii_table
}
table_data_manager.insert_multiple_tables(tables_data)
```

### Using Data Snapshots

```python
def test_with_sql_data(self, data_snapshot_manager):
    # Load data from SQL
    sql_data = """
    INSERT INTO user_broker_credentials (user_id, broker_name, api_key, status) VALUES
    ('12345678-1234-1234-1234-123456789012', 'zerodha', 'test_key', 'active');
    """
    data_snapshot_manager.load_from_sql(sql_data)
    
    # Capture state
    snapshot = data_snapshot_manager.capture_snapshot('user_broker_credentials')
    
    # Export as SQL
    sql_output = data_snapshot_manager.export_table_as_sql('user_broker_credentials')
```

### Mocking External APIs

```python
from unittest.mock import patch, MagicMock

def test_with_external_api_mock(self):
    with patch('integration_service.lib.broker.kite_user.KiteConnect') as mock_kite:
        mock_instance = MagicMock()
        mock_kite.return_value = mock_instance
        mock_instance.login_url.return_value = 'https://example.com/login'
        
        # Your test code here
        # Only the external API call is mocked, everything else is real
```

## Available Fixtures

### Database Fixtures

- `db` - Provides database access with automatic transaction rollback
- `clean_db` - Provides completely clean database state
- `django_db_setup` - Sets up test database schema

### Test Data Fixtures

- `test_user_id` - Provides a consistent UUID for testing
- `sample_broker_credential_data` - Provides ASCII table data for active broker credential
- `pending_broker_credential_data` - Provides ASCII table data for pending broker credential
- `authenticated_request_factory` - Factory for creating authenticated requests

### Utility Fixtures

- `table_data_manager` - Provides ASCII table data manager (manual cleanup)

- `mock_kite_api` - Provides mock data for Kite API responses  
- `api_credentials` - Provides test API credentials

## ASCII Table Data Utilities

The `TableDataManager` class provides powerful utilities for handling test data in ASCII table format:

### Key Methods

- `insert_table_data(table_name, ascii_table)` - Insert data from ASCII table format
- `insert_multiple_tables(tables_data)` - Insert data for multiple tables
- `cleanup(specific_tables)` - Clean up data inserted by this instance
- `get_inserted_data(table_name)` - Get data that was inserted for tracking
- `export_table_as_ascii(table_name)` - Export table data as ASCII format
- `clear_table_completely(table_name)` - Clear all data from table

### Example Usage

```python
# Create a table data manager
manager = TableDataManager()

# Load test data using readable ASCII table format
credentials_table = """
+--------------------------------------+-------------+----------+---------------------+
| user_id                              | broker_name | api_key  | status              |
+--------------------------------------+-------------+----------+---------------------+
| 12345678-1234-1234-1234-123456789012 | zerodha     | key1     | active              |
| 87654321-4321-4321-4321-210987654321 | zerodha     | key2     | pending_verification|
+--------------------------------------+-------------+----------+---------------------+
"""

# Insert the data (automatically tracked)
result = manager.insert_table_data('user_broker_credentials', credentials_table)
assert result == 2  # 2 rows inserted

# Run your test...

# Clean up only the data this manager inserted
manager.cleanup()
```

## Best Practices

### 1. Test Isolation
- Each test should start with a clean database state
- Use transactions for automatic rollback
- Don't rely on data from other tests

### 2. Real Database Interactions
- Use actual database operations, not mocks
- Test complete request/response flows
- Verify database state changes

### 3. Minimal Mocking
- Only mock external APIs (Kite, broker APIs)
- Don't mock internal application logic
- Don't mock database operations

### 4. Comprehensive Coverage
- Test happy paths and error conditions
- Test different user states and scenarios
- Test edge cases and boundary conditions

### 5. Clear Test Names
- Use descriptive test names that explain the scenario
- Include expected outcome in test name
- Group related tests in classes

### 6. Data Management
- Use factories for creating test data
- Use data snapshots for complex scenarios
- Clean up test data appropriately

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify test database exists and is accessible
   - Check environment variables
   - Ensure migrations have been run

2. **Import Errors**
   - Make sure all dependencies are installed
   - Check PYTHONPATH includes project root
   - Verify Django settings are correct

3. **Test Isolation Issues**
   - Tests affecting each other usually indicates missing `@pytest.mark.requires_db`
   - Check that fixtures are properly configured
   - Verify transaction rollback is working

4. **Slow Tests**
   - Use `pytest -n auto` for parallel execution
   - Consider using `--disable-warnings` to reduce output
   - Profile tests to identify bottlenecks

### Debug Mode

Run tests with verbose output and debugging:

```bash
# Verbose output
pytest -v

# Show print statements
pytest -s

# Debug mode (drop into pdb on failures)
pytest --pdb

# Show locals in tracebacks
pytest --tb=long
```

## Contributing

When adding new tests:

1. Follow the established patterns and conventions
2. Use appropriate markers (`@pytest.mark.integration`, etc.)
3. Include comprehensive docstrings
4. Test both success and failure scenarios
5. Use the data snapshot utilities for complex scenarios
6. Keep mocking minimal and focused on external dependencies

## Examples

See `tests/integration_service/test_kite_auth_views.py` for comprehensive examples of:
- Integration testing with real database
- Data snapshot usage
- Factory pattern for test data
- Complete request/response flow testing
- Error handling verification 