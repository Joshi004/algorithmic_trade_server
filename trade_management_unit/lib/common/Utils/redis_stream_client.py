import redis
import json
import os
from trade_management_unit.lib.common.Utils.custome_logger import log



class RedisStreamClient:
    """
    Redis Stream client for publishing events to Redis streams.
    Uses fire-and-forget approach with comprehensive error logging.
    """
    
    def __init__(self):
        """Initialize Redis connection using environment variables"""
        self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
        self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
        self.redis_db = 0
        # Socket timeout (in seconds) - If Redis operations like connect/read/write take longer than this, they will timeout
        self.connection_timeout = 5  # Both socket_timeout and socket_connect_timeout in Redis client
        self._client = None
    
    def _get_redis_client(self):
        """Get Redis client with connection pooling and timeout handling"""
        try:
            if self._client is None:
                self._client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    db=self.redis_db,
                    socket_timeout=self.connection_timeout,
                    socket_connect_timeout=self.connection_timeout,
                    decode_responses=True,
                    health_check_interval=30
                )
            return self._client
        except Exception as e:
            log(f"Failed to create Redis client: {str(e)}", level="error")
            return None
    
    def publish_to_stream(self, stream_name, event_data):
        """
        Publish event data to Redis stream.
        
        Args:
            stream_name (str): Name of the Redis stream
            event_data (dict): Event data to publish
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            client = self._get_redis_client()
            if client is None:
                log(f"Redis client unavailable, cannot publish to stream '{stream_name}'", level="error")
                return False
            
            # Test Redis connection
            client.ping()
            
            # Flatten the event data for Redis stream format
            flattened_data = self._flatten_dict(event_data)
            
            # Add to stream
            stream_id = client.xadd(stream_name, flattened_data)
            
            log(f"Successfully published event to stream '{stream_name}' with ID: {stream_id}")
            return True
            
        except redis.ConnectionError as e:
            log(f"Redis connection error while publishing to stream '{stream_name}': {str(e)}", level="error")
            return False
        except redis.TimeoutError as e:
            log(f"Redis timeout error while publishing to stream '{stream_name}': {str(e)}", level="error")
            return False
        except Exception as e:
            log(f"Unexpected error while publishing to stream '{stream_name}': {str(e)}", level="error")
            return False
    
    def _flatten_dict(self, data, parent_key='', separator='_'):
        """
        Flatten nested dictionary for Redis stream format.
        
        Args:
            data (dict): Dictionary to flatten
            parent_key (str): Parent key for nested items
            separator (str): Separator for nested keys
            
        Returns:
            dict: Flattened dictionary
        """
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, separator).items())
            elif isinstance(value, (list, tuple)):
                # Convert lists/tuples to JSON strings
                items.append((new_key, json.dumps(value)))
            elif value is None:
                items.append((new_key, ''))
            else:
                items.append((new_key, str(value)))
        
        return dict(items)
    
    def health_check(self):
        """
        Check if Redis connection is healthy.
        
        Returns:
            bool: True if Redis is reachable, False otherwise
        """
        try:
            client = self._get_redis_client()
            if client is None:
                return False
            
            client.ping()
            return True
        except Exception as e:
            log(f"Redis health check failed: {str(e)}", level="error")
            return False
    
    def close_connection(self):
        """Close Redis connection"""
        try:
            if self._client:
                self._client.close()
                self._client = None
                log("Redis connection closed")
        except Exception as e:
            log(f"Error closing Redis connection: {str(e)}", level="error")


# Singleton instance for reuse across the application
_redis_client_instance = None

def get_redis_stream_client():
    """
    Get singleton Redis stream client instance.
    
    Returns:
        RedisStreamClient: Redis stream client instance
    """
    global _redis_client_instance
    if _redis_client_instance is None:
        _redis_client_instance = RedisStreamClient()
    return _redis_client_instance 