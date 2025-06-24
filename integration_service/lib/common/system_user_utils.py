"""
System user utilities for Integration Service

This module provides utilities for managing system-level users and credentials
that are used for cross-service operations.
"""

import time
from django.core.cache import cache
from django.contrib.auth import get_user_model
from integration_service.lib.utils.logger import log

# Cache configuration
ADMIN_USER_CACHE_KEY = "system_admin_user_id"
ADMIN_USER_CACHE_TTL = 3600  # 1 hour

User = get_user_model()

def get_system_admin_user_id():
    """
    Get the system admin user ID with caching.
    
    The system admin user is used for internal operations that require
    a valid user context but are not tied to a specific end user.
    
    Returns:
        str: Public ID of the system admin user
        
    Raises:
        RuntimeError: If system admin user is not found
    """
    # Try to get from cache first
    cached_admin_id = cache.get(ADMIN_USER_CACHE_KEY)
    if cached_admin_id:
        log(f"Retrieved admin user ID from cache: {cached_admin_id}", level="debug")
        return cached_admin_id
    
    try:
        # Look for admin user by username
        admin_user = User.objects.get(email='admin@ats.com')
        admin_public_id = admin_user.public_id
        
        # Cache the result for future use
        cache.set(ADMIN_USER_CACHE_KEY, admin_public_id, ADMIN_USER_CACHE_TTL)
        
        log(f"Retrieved and cached admin user ID: {admin_public_id}", level="info")
        return admin_public_id
        
    except User.DoesNotExist:
        error_msg = "System admin user not found. Please ensure an admin user exists in the database."
        log(f"Error getting system admin user ID: {error_msg}", level="error")
        raise RuntimeError(error_msg)
    except Exception as e:
        log(f"Error getting system admin user ID: {str(e)}", level="error")
        raise

def get_system_user_credentials():
    """
    Get system user credentials for broker operations.
    
    Returns:
        dict: System user credentials
        
    Note: This is a placeholder implementation. In production,
          credentials should be securely managed and retrieved.
    """
    return {
        'user_id': get_system_admin_user_id(),
        'broker_user_id': 'system',
        'api_key': 'system_api_key',  # Should be from secure config
        'access_token': 'system_access_token'  # Should be from secure config
    }

def clear_system_admin_user_cache():
    """
    Clear the cached system admin user ID.
    Useful for cache invalidation when admin user is updated.
    """
    cache.delete(ADMIN_USER_CACHE_KEY)
    log("Cleared system admin user cache", level="info")

def is_system_user(user_id):
    """
    Check if the given user_id belongs to the system admin user.
    
    Args:
        user_id (str): User ID to check
        
    Returns:
        bool: True if user_id belongs to system admin user
    """
    try:
        system_user_id = get_system_admin_user_id()
        return str(user_id) == system_user_id
    except Exception:
        return False

# For backward compatibility and easy access
def get_admin_user_id():
    """
    Alias for get_system_admin_user_id() for backward compatibility.
    
    Returns:
        str: The admin user's public_id
    """
    return get_system_admin_user_id() 