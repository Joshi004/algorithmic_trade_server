-- Create test database
CREATE DATABASE IF NOT EXISTS test_ats_db;

-- Grant privileges to ats_user for both normal and test database
GRANT ALL PRIVILEGES ON ats_db.* TO 'ats_user'@'%';
GRANT ALL PRIVILEGES ON test_ats_db.* TO 'ats_user'@'%';

-- Ensure test_% databases can be created and dropped by ats_user (needed for Django tests)
GRANT ALL PRIVILEGES ON `test\_%`.* TO 'ats_user'@'%';

-- Apply changes
FLUSH PRIVILEGES;
