#!/bin/bash

# Enhanced Docker Test Runner Script
# Runs Django tests inside Docker container with improved error handling
# Usage: ./docker_run_tests.sh [app_name.tests.test_module] [--keepdb]

# Set default values
TEST_PATH=${1:-"ats_gateway.tests"}
OPTIONS=${2:-""}

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"  # Change to script directory

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found. Please install Docker to run tests in a container."
    echo "Alternatively, you can try running tests locally if Django is installed:"
    echo "  ./run_tests.sh $TEST_PATH $OPTIONS"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running. Please start Docker."
    exit 1
fi

# Get container ID
CONTAINER_ID=$(docker ps -qf "name=ats-django-app")

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: ats-django-app container is not running."
    
    # Ask if user wants to start containers
    echo -n "Do you want to start the Docker containers? (y/n): "
    read -r START_CONTAINERS
    
    if [[ "$START_CONTAINERS" =~ ^[Yy]$ ]]; then
        echo "Starting Docker containers..."
        docker-compose up -d
        
        # Wait a bit for containers to start
        echo "Waiting for containers to start..."
        sleep 5
        
        # Check if container started successfully
        CONTAINER_ID=$(docker ps -qf "name=ats-django-app")
        if [ -z "$CONTAINER_ID" ]; then
            echo "Failed to start ats-django-app container."
            exit 1
        fi
    else
        echo "Start the containers with: docker-compose up -d"
        exit 1
    fi
fi

echo "==========================================="
echo "Running tests in Docker container"
echo "Container ID: $CONTAINER_ID"
echo "Test path: $TEST_PATH"
echo "Options: $OPTIONS"
echo "==========================================="

# Run the tests in the container with test settings
docker exec -it $CONTAINER_ID bash -c "DJANGO_SETTINGS_MODULE=ats_base.test_settings python manage.py test $TEST_PATH $OPTIONS"

# Store the exit code
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "==========================================="
    echo "Tests failed with exit code: $EXIT_CODE"
    echo "==========================================="
else
    echo "==========================================="
    echo "All tests passed successfully!"
    echo "==========================================="
fi

exit $EXIT_CODE
