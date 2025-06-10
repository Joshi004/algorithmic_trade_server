"""
Redis Consumer Client for Scanning Service.
Optimized for blocking read operations and consumer group management.
"""
import redis
import time
from typing import Optional, List, Dict, Any
from scanning_service.lib.utils.logger import log
from ..common.base_client import BaseRedisClient


class ConsumerRedisClient(BaseRedisClient):
    """Redis client optimized for consuming events with blocking operations"""
    
    def __init__(self, consumer_group: str, consumer_name: str):
        """
        Initialize consumer Redis client
        
        Args:
            consumer_group: Name of the consumer group
            consumer_name: Unique name for this consumer instance
        """
        super().__init__("consumer")
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
    
    def _get_client_config(self) -> dict:
        """Get consumer-specific Redis configuration"""
        return self.config.get_consumer_config()
    
    def ensure_consumer_group(self, stream_name: str, start_id: str = '0') -> bool:
        """
        Ensure consumer group exists for the stream
        
        Args:
            stream_name: Name of the Redis stream
            start_id: Starting position for the consumer group ('0' for beginning, '$' for latest)
            
        Returns:
            True if group exists or was created, False otherwise
        """
        try:
            client = self.get_client()
            if client is None:
                return False
            
            # Try to create the consumer group
            try:
                client.xgroup_create(stream_name, self.consumer_group, id=start_id, mkstream=True)
                log(f"Created consumer group '{self.consumer_group}' for stream '{stream_name}'")
                return True
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    log(f"Consumer group '{self.consumer_group}' already exists for stream '{stream_name}'")
                    return True
                else:
                    log(f"Error creating consumer group: {str(e)}", level="error")
                    return False
                    
        except Exception as e:
            log(f"Error ensuring consumer group: {str(e)}", level="error")
            return False
    
    def read_from_stream(
        self, 
        stream_name: str, 
        count: Optional[int] = None, 
        block: Optional[int] = None
    ) -> List[tuple]:
        """
        Read messages from stream using consumer group
        
        Args:
            stream_name: Name of the Redis stream
            count: Maximum number of messages to read
            block: Block for specified milliseconds if no messages (None = don't block)
            
        Returns:
            List of (stream_name, messages) tuples
        """
        try:
            client = self.get_client()
            if client is None:
                return []
            
            # Use consumer configuration defaults if not specified
            if count is None:
                count = self.config.consumer_batch_size
            if block is None:
                block = self.config.consumer_timeout
            
            # Read messages from stream
            messages = client.xreadgroup(
                self.consumer_group,
                self.consumer_name,
                {stream_name: '>'},
                count=count,
                block=block
            )
            
            return messages
            
        except redis.ConnectionError as e:
            log(f"Redis connection error while reading from '{stream_name}': {str(e)}", level="error")
            return []
        except redis.TimeoutError:
            # Timeout is expected when no messages are available
            return []
        except Exception as e:
            log(f"Error reading from stream '{stream_name}': {str(e)}", level="error")
            return []
    
    def acknowledge_message(self, stream_name: str, message_id: str) -> bool:
        """
        Acknowledge processing of a message
        
        Args:
            stream_name: Name of the Redis stream
            message_id: ID of the message to acknowledge
            
        Returns:
            True if acknowledged successfully, False otherwise
        """
        try:
            client = self.get_client()
            if client is None:
                return False
            
            result = client.xack(stream_name, self.consumer_group, message_id)
            if result:
                log(f"Acknowledged message {message_id} from stream '{stream_name}'")
            return bool(result)
            
        except Exception as e:
            log(f"Error acknowledging message {message_id}: {str(e)}", level="error")
            return False
    



def create_consumer_client(consumer_group: str, consumer_name: Optional[str] = None) -> ConsumerRedisClient:
    """
    Create a new consumer Redis client instance
    
    Args:
        consumer_group: Name of the consumer group
        consumer_name: Unique name for this consumer (auto-generated if None)
        
    Returns:
        ConsumerRedisClient instance
    """
    if consumer_name is None:
        consumer_name = f"consumer_{int(time.time() * 1000)}"
    
    return ConsumerRedisClient(consumer_group, consumer_name) 