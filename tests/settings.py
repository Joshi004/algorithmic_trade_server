# Test settings that inherit from main settings but override for testing
from ats_base.settings import *
import os

# Override database configuration for testing
# Supports both container and local testing environments
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('TEST_DATABASE_NAME', 'ats_db_test'),  # Configurable test database name
        'USER': os.environ.get('TEST_DATABASE_USER', 'ats_user'),  # Use ats_user from container
        'PASSWORD': os.environ.get('TEST_DATABASE_PASSWORD', 'ats_password'),  # Use container password
        'HOST': os.environ.get('TEST_DATABASE_HOST', 'ats-db'),  # Container database host
        'PORT': os.environ.get('TEST_DATABASE_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'TEST': {
            'NAME': os.environ.get('TEST_DATABASE_NAME', 'ats_db_test'),
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        }
    }
}

# Disable migrations for faster test runs
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

# Comment out the line below if you want to run migrations during tests
# MIGRATION_MODULES = DisableMigrations()

# For container testing, always use clean test database without copying production data
DATABASES['default']['TEST']['SERIALIZE'] = False

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging during tests to reduce noise
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
    'loggers': {
        'ats_gateway': {'handlers': ['null'], 'level': 'INFO', 'propagate': False},
        'trade_management_unit': {'handlers': ['null'], 'level': 'INFO', 'propagate': False},
        'scanning_service': {'handlers': ['null'], 'level': 'INFO', 'propagate': False},
        'integration_service': {'handlers': ['null'], 'level': 'INFO', 'propagate': False},
        'initiation_service': {'handlers': ['null'], 'level': 'INFO', 'propagate': False},
    }
}

# Override Redis configuration for testing (use different DB)
REDIS_HOST = os.environ.get('TEST_REDIS_HOST', 'ats-redis')  # Container Redis host
REDIS_PORT = int(os.environ.get('TEST_REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('TEST_REDIS_DB', 1))  # Use different DB for tests

# Test-specific email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable CSRF for testing
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Use in-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Test-specific media settings
MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')

# Disable CORS for testing
CORS_ALLOW_ALL_ORIGINS = True 