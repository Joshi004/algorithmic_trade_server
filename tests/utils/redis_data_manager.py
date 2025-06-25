"""
Redis Data Manager for handling Redis test data management.

This utility allows you to:
1. Set up Redis data for testing
2. Track what data was inserted by each instance
3. Clean up only the data inserted by that specific instance
4. Support multiple Redis streams and keys per test instance

Usage Examples:
    # Create a Redis data manager instance
    redis_manager = RedisDataManager()
    
    # Insert stream data
    redis_manager.insert_stream_data('scanning_queue', {
        'field1': 'value1',
        'field2': 'value2'
    })
    
    # Insert key-value data
    redis_manager.set_key_data('test_key', 'test_value')
    
    # Run your tests...
    
    # Clean up only data inserted by this instance
    redis_manager.cleanup()
"""

import redis
import uuid
from typing import Dict, List, Any, Optional, Set
from django.conf import settings
from datetime import datetime


class RedisDataManager:
    """
    Manages test data in Redis with instance-based tracking and cleanup.
    """
    
    def __init__(self):
        """Initialize the Redis data manager with tracking."""
        self.inserted_streams: Dict[str, List[str]] = {}  # stream_name -> list of entry IDs
        self.inserted_keys: Set[str] = set()  # Set of keys inserted by this instance
        self._instance_id = str(uuid.uuid4())[:8]
        
        # Initialize Redis client
        self.redis_client = self._get_redis_client()
        
    def _get_redis_client(self):
        """Get Redis client using Django settings"""
        redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
        redis_port = getattr(settings, 'REDIS_PORT', 6379)
        redis_db = getattr(settings, 'REDIS_DB', 0)
        
        return redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
    
    def insert_stream_data(self, stream_name: str, data: Dict[str, Any]) -> str:
        """
        Insert data into a Redis stream.
        
        Args:
            stream_name: Name of the Redis stream
            data: Dictionary of field-value pairs to insert
            
        Returns:
            Entry ID of the inserted data
        """
        try:
            # Add instance ID to track this insertion
            data_with_tracking = {**data, '_test_instance_id': self._instance_id}
            
            # Insert into stream
            entry_id = self.redis_client.xadd(stream_name, data_with_tracking)
            
            # Track for cleanup
            if stream_name not in self.inserted_streams:
                self.inserted_streams[stream_name] = []
            self.inserted_streams[stream_name].append(entry_id)
            
            return entry_id
        except Exception as e:
            raise Exception(f"Failed to insert stream data: {str(e)}")
    
    def set_key_data(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis.
        
        Args:
            key: Redis key
            value: Value to set
            ex: Optional expiration time in seconds
            
        Returns:
            True if successful
        """
        try:
            # Add instance tracking to the key
            tracked_key = f"{key}:{self._instance_id}"
            
            result = self.redis_client.set(tracked_key, value, ex=ex)
            
            # Track for cleanup
            self.inserted_keys.add(tracked_key)
            
            return result
        except Exception as e:
            raise Exception(f"Failed to set key data: {str(e)}")
    
    def get_key_data(self, key: str) -> Any:
        """
        Get value for a tracked key.
        
        Args:
            key: Original key name (without instance tracking)
            
        Returns:
            Value or None if not found
        """
        try:
            tracked_key = f"{key}:{self._instance_id}"
            return self.redis_client.get(tracked_key)
        except Exception as e:
            raise Exception(f"Failed to get key data: {str(e)}")
    
    def insert_hash_data(self, hash_key: str, field_values: Dict[str, Any]) -> int:
        """
        Insert field-value pairs into a Redis hash.
        
        Args:
            hash_key: Name of the Redis hash
            field_values: Dictionary of field-value pairs
            
        Returns:
            Number of fields that were added
        """
        try:
            # Add instance tracking
            tracked_hash_key = f"{hash_key}:{self._instance_id}"
            
            result = self.redis_client.hset(tracked_hash_key, mapping=field_values)
            
            # Track for cleanup
            self.inserted_keys.add(tracked_hash_key)
            
            return result
        except Exception as e:
            raise Exception(f"Failed to insert hash data: {str(e)}")
    
    def clear_stream_completely(self, stream_name: str) -> bool:
        """
        Clear ALL data from a Redis stream (not just data inserted by this instance).
        Use with caution!
        
        Args:
            stream_name: Name of the stream to clear
            
        Returns:
            True if successful
        """
        try:
            # Delete the entire stream
            return self.redis_client.delete(stream_name) > 0
        except Exception as e:
            raise Exception(f"Failed to clear stream: {str(e)}")
    
    def clear_key_completely(self, key: str) -> bool:
        """
        Clear a specific key from Redis completely.
        
        Args:
            key: Key to delete
            
        Returns:
            True if successful
        """
        try:
            return self.redis_client.delete(key) > 0
        except Exception as e:
            raise Exception(f"Failed to clear key: {str(e)}")
    
    def cleanup(self, specific_streams: Optional[List[str]] = None, 
                specific_keys: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Clean up data inserted by this instance.
        
        Args:
            specific_streams: If provided, only clean these streams
            specific_keys: If provided, only clean these keys
            
        Returns:
            Dictionary with cleanup results
        """
        results = {
            'streams_cleaned': 0,
            'stream_entries_deleted': 0,
            'keys_deleted': 0
        }
        
        # Clean streams
        streams_to_clean = specific_streams if specific_streams else list(self.inserted_streams.keys())
        
        for stream_name in streams_to_clean:
            if stream_name in self.inserted_streams:
                entry_ids = self.inserted_streams[stream_name]
                try:
                    # Delete specific entries from stream
                    if entry_ids:
                        deleted_count = self.redis_client.xdel(stream_name, *entry_ids)
                        results['stream_entries_deleted'] += deleted_count
                        results['streams_cleaned'] += 1
                except Exception:
                    pass  # Continue cleanup even if some entries fail
                
                # Remove from tracking
                del self.inserted_streams[stream_name]
        
        # Clean keys
        keys_to_clean = specific_keys if specific_keys else list(self.inserted_keys)
        
        if keys_to_clean:
            try:
                deleted_count = self.redis_client.delete(*keys_to_clean)
                results['keys_deleted'] = deleted_count
            except Exception:
                pass  # Continue cleanup even if some keys fail
        
        # Clear tracking
        if not specific_keys:
            self.inserted_keys.clear()
        else:
            for key in keys_to_clean:
                self.inserted_keys.discard(key)
        
        return results
    
    def get_stream_length(self, stream_name: str) -> int:
        """
        Get the length of a Redis stream.
        
        Args:
            stream_name: Name of the stream
            
        Returns:
            Number of entries in the stream
        """
        try:
            return self.redis_client.xlen(stream_name)
        except Exception as e:
            raise Exception(f"Failed to get stream length: {str(e)}")
    
    def get_all_tracked_streams(self) -> List[str]:
        """
        Get list of all streams that have data inserted by this instance.
        
        Returns:
            List of stream names
        """
        return list(self.inserted_streams.keys())
    
    def get_all_tracked_keys(self) -> List[str]:
        """
        Get list of all keys that were set by this instance.
        
        Returns:
            List of key names
        """
        return list(self.inserted_keys)
    
    def ping(self) -> bool:
        """
        Test Redis connection.
        
        Returns:
            True if Redis is reachable
        """
        try:
            return self.redis_client.ping()
        except Exception:
            return False 