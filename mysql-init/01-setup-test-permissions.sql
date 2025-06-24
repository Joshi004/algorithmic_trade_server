-- MySQL initialization script for ATS test database permissions
-- This script runs automatically when the MySQL container starts for the first time

-- Grant permissions for parallel test execution
-- pytest-xdist creates databases like ats_db_test_gw0, ats_db_test_gw1, etc.
GRANT ALL PRIVILEGES ON `ats_db_test_%`.* TO 'ats_user'@'%';

-- Ensure the main test database exists and has proper permissions
CREATE DATABASE IF NOT EXISTS ats_db_test;
GRANT ALL PRIVILEGES ON `ats_db_test`.* TO 'ats_user'@'%';

-- Flush privileges to apply changes
FLUSH PRIVILEGES;

-- Log the setup completion
SELECT 'Test database permissions configured successfully!' AS message; 