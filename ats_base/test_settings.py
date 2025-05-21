"""
Django test settings for ats_base project.

These settings extend the base settings.py but configure the system to use
the test database and make other test-specific adjustments.
"""

from .settings import *

# Use test database
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DATABASE_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.environ.get('TEST_DATABASE_NAME', 'test_ats_db'),
        'USER': os.environ.get('DATABASE_USER', 'ats_user'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', 'ats_password'),
        'HOST': os.environ.get('DATABASE_HOST', 'ats-db'),
        'PORT': os.environ.get('DATABASE_PORT', '3306'),
        'TEST': {
            'NAME': 'test_ats_db',
            'CHARSET': 'utf8',
            'COLLATION': 'utf8_general_ci',
        },
    }
}

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use in-memory storage for static/media files during tests
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'

# Disable logging during tests
import logging
logging.disable(logging.CRITICAL)

# Use a faster, simpler test runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Make tests faster by simplifying password validation
AUTH_PASSWORD_VALIDATORS = []

# Cache in memory during tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
