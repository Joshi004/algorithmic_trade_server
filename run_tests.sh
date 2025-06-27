#!/bin/bash
# ATS Testing Script - Docker Container Version
# This script runs the test suite inside the Docker container environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_DB_NAME="ats_db_test"
COVERAGE_THRESHOLD=65
PARALLEL_WORKERS="1"
VERBOSE=false
COVERAGE=true
TEST_PATTERN=""
CONTAINER_NAME="ats-django-app"
DB_CONTAINER_NAME="ats-mysql-db"

# Print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Docker Container Testing Script for ATS"
    echo "This script runs tests inside the Docker container environment."
    echo ""
    echo "Prerequisites:"
    echo "  - Docker containers must be running (docker-compose up -d)"
    echo "  - Container '${CONTAINER_NAME}' must be available"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -v, --verbose           Run tests in verbose mode"
    echo "  -c, --no-coverage       Skip coverage reporting"
    echo "  -p, --pattern PATTERN   Run tests matching pattern"
    echo "  -w, --workers NUM       Number of parallel workers (default: auto)"
    echo "  -t, --threshold NUM     Coverage threshold (default: 80)"
    echo "  -d, --db-name NAME      Test database name (default: ats_db_test)"
    echo "  -m, --markers MARKERS   Run tests with specific markers"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run all tests with coverage"
    echo "  $0 -v                   # Run all tests verbosely"
    echo "  $0 -p 'test_get_login'  # Run tests matching pattern"
    echo "  $0 -m integration       # Run only integration tests"
    echo "  $0 -c -w 4              # Run without coverage, 4 workers"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--no-coverage)
            COVERAGE=false
            shift
            ;;
        -p|--pattern)
            TEST_PATTERN="$2"
            shift 2
            ;;
        -w|--workers)
            PARALLEL_WORKERS="$2"
            shift 2
            ;;
        -t|--threshold)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        -d|--db-name)
            TEST_DB_NAME="$2"
            shift 2
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if containers are running
check_containers() {
    print_status $BLUE "Checking Docker containers..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_status $RED "Error: Docker not found. Please install Docker."
        exit 1
    fi
    
    # Check if app container is running
    if ! docker ps --filter "name=${CONTAINER_NAME}" --filter "status=running" --format "table {{.Names}}" | grep -q "${CONTAINER_NAME}"; then
        print_status $RED "Error: Container '${CONTAINER_NAME}' is not running."
        print_status $YELLOW "Please start containers with: docker-compose up -d"
        exit 1
    fi
    
    # Check if database container is running
    if ! docker ps --filter "name=${DB_CONTAINER_NAME}" --filter "status=running" --format "table {{.Names}}" | grep -q "${DB_CONTAINER_NAME}"; then
        print_status $RED "Error: Database container '${DB_CONTAINER_NAME}' is not running."
        print_status $YELLOW "Please start containers with: docker-compose up -d"
        exit 1
    fi
    
    print_status $GREEN "All required containers are running."
}

# Function to setup test database inside container
setup_test_database() {
    print_status $BLUE "Setting up test database..."
    
    # Create test database inside the MySQL container
    docker exec ${DB_CONTAINER_NAME} mysql -u root -prootpassword -e "
        CREATE DATABASE IF NOT EXISTS ${TEST_DB_NAME};
        GRANT ALL PRIVILEGES ON ${TEST_DB_NAME}.* TO 'ats_user'@'%';
        FLUSH PRIVILEGES;
    " 2>/dev/null || {
        print_status $YELLOW "Warning: Could not create test database. It may already exist."
    }
    
    print_status $GREEN "Test database setup completed."
}

# Function to run migrations inside container
run_migrations() {
    print_status $BLUE "Running test database migrations inside container..."
    
    if docker exec ${CONTAINER_NAME} python manage.py migrate --settings=tests.settings --verbosity=0; then
        print_status $GREEN "Migrations completed successfully."
    else
        print_status $RED "Migration failed!"
        exit 1
    fi
}

# Function to build pytest command
build_pytest_command() {
    local cmd="pytest"
    
    # Add verbosity
    if [[ "$VERBOSE" == "true" ]]; then
        cmd="$cmd -v"
    fi
    
    # Add coverage options
    if [[ "$COVERAGE" == "true" ]]; then
        cmd="$cmd --cov=."
        cmd="$cmd --cov-report=html:htmlcov"
        cmd="$cmd --cov-report=term-missing"
        cmd="$cmd --cov-fail-under=$COVERAGE_THRESHOLD"
    fi
    
    # Add parallel execution
    if [[ "$PARALLEL_WORKERS" != "1" ]]; then
        cmd="$cmd -n $PARALLEL_WORKERS"
    fi
    
    # Add markers
    if [[ -n "$MARKERS" ]]; then
        cmd="$cmd -m $MARKERS"
    fi
    
    # Add test pattern
    if [[ -n "$TEST_PATTERN" ]]; then
        cmd="$cmd -k $TEST_PATTERN"
    fi
    
    # Add other useful options
    cmd="$cmd --tb=short"
    cmd="$cmd --strict-markers"
    cmd="$cmd --disable-warnings"
    
    echo "$cmd"
}

# Function to display test summary
display_summary() {
    local exit_code=$1
    
    echo ""
    print_status $BLUE "=================================================="
    
    if [[ $exit_code -eq 0 ]]; then
        print_status $GREEN "✓ All tests passed successfully!"
        
        if [[ "$COVERAGE" == "true" ]]; then
            print_status $GREEN "✓ Coverage threshold met (>= ${COVERAGE_THRESHOLD}%)"
            print_status $BLUE "Coverage report generated: htmlcov/index.html"
        fi
    else
        print_status $RED "✗ Some tests failed!"
        
        if [[ "$COVERAGE" == "true" ]]; then
            print_status $YELLOW "Coverage report generated: htmlcov/index.html"
        fi
    fi
    
    print_status $BLUE "=================================================="
}

# Main execution
main() {
    print_status $BLUE "Starting ATS Test Suite (Docker Container Mode)"
    print_status $BLUE "================================================"
    
    # Check prerequisites
    print_status $BLUE "Checking prerequisites..."
    
    # Check containers
    check_containers
    
    # Setup test database
    setup_test_database
    
    # Run migrations
    run_migrations
    
    # Build pytest command
    pytest_cmd=$(build_pytest_command)
    
    # Prepare Docker exec command
    docker_cmd="docker exec ${CONTAINER_NAME} bash -c 'cd /app && export TEST_DATABASE_NAME=${TEST_DB_NAME} && export DJANGO_SETTINGS_MODULE=tests.settings && ${pytest_cmd}'"
    
    print_status $BLUE "Running command inside container: ${pytest_cmd}"
    echo ""
    
    # Run tests inside container
    if eval "$docker_cmd"; then
        display_summary 0
        
        # Copy coverage report to host (if coverage was enabled)
        if [[ "$COVERAGE" == "true" ]]; then
            print_status $BLUE "Copying coverage report from container..."
            docker cp ${CONTAINER_NAME}:/app/htmlcov ./htmlcov 2>/dev/null || {
                print_status $YELLOW "Warning: Could not copy coverage report from container."
            }
        fi
        
        exit 0
    else
        display_summary 1
        
        # Still try to copy coverage report on failure for debugging
        if [[ "$COVERAGE" == "true" ]]; then
            docker cp ${CONTAINER_NAME}:/app/htmlcov ./htmlcov 2>/dev/null || true
        fi
        
        exit 1
    fi
}

# Run main function
main "$@" 