"""
Redis Publisher Client for Scanning Service.
Optimized for fast, non-blocking publish operations.
"""
import redis
from typing import Optional
from scanning_service.lib.utils.logger import log
from ..common.base_client import BaseRedisClient


class PublisherRedisClient(BaseRedisClient):
    """Redis client optimized for publishing events"""
    
    def __init__(self):
        """Initialize publisher Redis client"""
        super().__init__("publisher")
    
    def _get_client_config(self) -> dict:
        """Get publisher-specific Redis configuration"""
        return self.config.get_publisher_config()
    
    def publish_to_stream(self, stream_name: str, data: dict) -> Optional[str]:
        """
        Publish data to Redis stream
        
        Args:
            stream_name: Name of the Redis stream
            data: Data dictionary to publish
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            client = self.get_client()
            if client is None:
                log(f"Publisher client unavailable, cannot publish to stream '{stream_name}'", level="error")
                return None
            
            # Add to stream
            message_id = client.xadd(stream_name, data)
            log(f"Published to stream '{stream_name}' with ID: {message_id}")
            return message_id
            
        except redis.ConnectionError as e:
            log(f"Redis connection error while publishing to '{stream_name}': {str(e)}", level="error")
            return None
        except redis.TimeoutError as e:
            log(f"Redis timeout error while publishing to '{stream_name}': {str(e)}", level="error")
            return None
        except Exception as e:
            log(f"Unexpected error while publishing to '{stream_name}': {str(e)}", level="error")
            return None
    
    def publish_batch_to_stream(self, stream_name: str, data_list: list) -> int:
        """
        Publish multiple data items to Redis stream in batch
        
        Args:
            stream_name: Name of the Redis stream
            data_list: List of data dictionaries to publish
            
        Returns:
            Number of successfully published messages
        """
        if not data_list:
            return 0
        
        published_count = 0
        client = self.get_client()
        
        if client is None:
            log(f"Publisher client unavailable, cannot publish batch to stream '{stream_name}'", level="error")
            return 0
        
        try:
            # Use pipeline for batch operations
            with client.pipeline() as pipe:
                for data in data_list:
                    pipe.xadd(stream_name, data)
                
                # Execute all commands
                results = pipe.execute()
                published_count = len([r for r in results if r])
                
            log(f"Published {published_count}/{len(data_list)} messages to stream '{stream_name}'")
            return published_count
            
        except Exception as e:
            log(f"Error in batch publish to '{stream_name}': {str(e)}", level="error")
            return published_count
    
    def get_stream_info(self, stream_name: str) -> dict:
        """
        Get information about a Redis stream
        
        Args:
            stream_name: Name of the Redis stream
            
        Returns:
            Stream information dictionary
        """
        try:
            client = self.get_client()
            if client is None:
                return {}
            
            return client.xinfo_stream(stream_name)
            
        except redis.ResponseError as e:
            if "no such key" in str(e).lower():
                log(f"Stream '{stream_name}' does not exist")
                return {'length': 0, 'exists': False}
            else:
                log(f"Error getting stream info for '{stream_name}': {str(e)}", level="error")
                return {}
        except Exception as e:
            log(f"Error getting stream info for '{stream_name}': {str(e)}", level="error")
            return {}
    



# Singleton instance for publisher client
_publisher_client = None

def get_publisher_client() -> PublisherRedisClient:
    """
    Get or create singleton publisher Redis client instance
    
    Returns:
        PublisherRedisClient instance
    """
    global _publisher_client
    if _publisher_client is None:
        _publisher_client = PublisherRedisClient()
    return _publisher_client 