"""
Configuration settings for Scanner State Management.
Provides centralized configuration for state persistence parameters.
"""

from django.conf import settings


class StateManagementConfig:
    """
    Configuration class for state management settings.
    Can be extended with database-driven configuration in the future.
    """
    
    # Default TTL for scanner state (in hours)
    DEFAULT_STATE_TTL_HOURS = getattr(settings, 'SCANNER_STATE_TTL_HOURS', 0.5)
    
    # Default progress update interval (number of instruments)
    DEFAULT_PROGRESS_UPDATE_INTERVAL = getattr(settings, 'SCANNER_PROGRESS_UPDATE_INTERVAL', 10)
    
    # Maximum age for state to be considered valid for resumption (in hours)
    MAX_STATE_AGE_HOURS = getattr(settings, 'SCANNER_MAX_STATE_AGE_HOURS', 2.0)
    
    # Redis key prefixes
    STATE_KEY_PREFIX = "scanner:state:"
    META_KEY_PREFIX = "scanner:meta:"
    
    @classmethod
    def get_state_ttl_seconds(cls, ttl_hours=None):
        """
        Get state TTL in seconds.
        
        Args:
            ttl_hours: Custom TTL in hours, uses default if None
            
        Returns:
            int: TTL in seconds
        """
        hours = ttl_hours or cls.DEFAULT_STATE_TTL_HOURS
        return int(hours * 3600)
    
    @classmethod
    def get_progress_update_interval(cls, custom_interval=None):
        """
        Get progress update interval.
        
        Args:
            custom_interval: Custom interval, uses default if None
            
        Returns:
            int: Number of instruments between progress updates
        """
        return custom_interval or cls.DEFAULT_PROGRESS_UPDATE_INTERVAL 