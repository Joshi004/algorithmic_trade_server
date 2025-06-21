"""
System User Utilities for Integration Service.

This module provides utilities to get the system admin user's credentials
for system-level operations like market data fetching, quote retrieval, etc.
"""
import logging
from django.core.cache import cache
from ats_gateway.models.User import User
from integration_service.models.UserBrokerCredential import UserBrokerCredential

logger = logging.getLogger(__name__)

# Cache key for admin user public_id
ADMIN_USER_CACHE_KEY = "system_admin_user_public_id"
ADMIN_USER_EMAIL = "admin@ats.com"

def get_system_user_id():
    """
    Get the system admin user's public_id for system-level operations.
    
    This function should be used when making API calls that require system-level
    access such as:
    - Fetching market quotes for scanning
    - Getting historical data for analysis
    - Retrieving instrument master data
    - Live market data streaming
    
    Returns:
        str: The admin user's public_id as a string
        
    Raises:
        RuntimeError: If admin user doesn't exist or doesn't have proper credentials
    """
    # Try to get from cache first
    cached_admin_id = cache.get(ADMIN_USER_CACHE_KEY)
    if cached_admin_id:
        logger.debug(f"Retrieved admin user ID from cache: {cached_admin_id}")
        return cached_admin_id
    
    # Get from database
    try:
        admin_user = User.objects.filter(email=ADMIN_USER_EMAIL).first()
        
        if not admin_user:
            raise RuntimeError(
                f"System admin user ({ADMIN_USER_EMAIL}) does not exist. "
                "Please create the admin user with proper broker credentials."
            )
        
        if not admin_user.is_active:
            raise RuntimeError(
                f"System admin user ({ADMIN_USER_EMAIL}) is not active. "
                "Please activate the admin user."
            )
        
        # Verify admin user has broker credentials
        credentials = UserBrokerCredential.objects.filter(
            user_id=admin_user.public_id,
            status='active'
        )
        
        if not credentials.exists():
            raise RuntimeError(
                f"System admin user ({ADMIN_USER_EMAIL}) does not have active broker credentials. "
                "Please register broker credentials for the admin user."
            )
        
        # Cache the result for 1 hour
        admin_public_id = str(admin_user.public_id)
        cache.set(ADMIN_USER_CACHE_KEY, admin_public_id, 3600)
        
        logger.info(f"Retrieved and cached admin user ID: {admin_public_id}")
        return admin_public_id
        
    except Exception as e:
        logger.error(f"Error getting system admin user ID: {str(e)}")
        raise RuntimeError(f"Failed to get system admin user ID: {str(e)}")

def is_system_user(user_id):
    """
    Check if the given user_id belongs to the system admin user.
    
    Args:
        user_id (str): User ID to check
        
    Returns:
        bool: True if user_id belongs to system admin user
    """
    try:
        system_user_id = get_system_user_id()
        return str(user_id) == system_user_id
    except Exception:
        return False

def clear_system_user_cache():
    """
    Clear the cached system admin user ID.
    Use this if admin user credentials are updated.
    """
    cache.delete(ADMIN_USER_CACHE_KEY)
    logger.info("Cleared system admin user cache")

# For backward compatibility and easy access
def get_admin_user_id():
    """
    Alias for get_system_user_id() for backward compatibility.
    
    Returns:
        str: The admin user's public_id
    """
    return get_system_user_id() 