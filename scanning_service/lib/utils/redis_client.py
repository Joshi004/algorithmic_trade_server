"""
Redis client utility for the scanning service.
Provides a singleton Redis connection for publishing events and managing distributed state.
"""
import redis
import os
from django.conf import settings
from scanning_service.lib.utils.logger import log

_redis_client = None

def get_redis_client():
    """
    Get or create a singleton Redis client instance.
    
    Returns:
        redis.Redis: Redis client instance
        
    Raises:
        redis.ConnectionError: If unable to connect to Redis
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            # Get Redis configuration from settings or environment
            redis_host = getattr(settings, 'REDIS_HOST', os.environ.get('REDIS_HOST', 'localhost'))
            redis_port = int(getattr(settings, 'REDIS_PORT', os.environ.get('REDIS_PORT', 6379)))
            redis_db = int(getattr(settings, 'REDIS_DB', os.environ.get('REDIS_DB', 0)))
            
            _redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            
            # Test the connection
            _redis_client.ping()
            log(f"Redis client initialized successfully - {redis_host}:{redis_port}")
            
        except redis.ConnectionError as e:
            log(f"Failed to connect to Redis: {str(e)}", level="error")
            raise
        except Exception as e:
            log(f"Failed to initialize Redis client: {str(e)}", level="error")
            raise
    
    return _redis_client

def close_redis_client():
    """
    Close the Redis client connection.
    """
    global _redis_client
    
    if _redis_client is not None:
        try:
            _redis_client.close()
            log("Redis client connection closed")
        except Exception as e:
            log(f"Error closing Redis client: {str(e)}", level="error")
        finally:
            _redis_client = None 