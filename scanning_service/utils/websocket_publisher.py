"""
WebSocket Publisher for Scanner Updates

This module provides utilities for publishing scanner updates to WebSocket subscribers
through the Django Channels framework.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from channels.layers import get_channel_layer
from django.conf import settings
import redis
from scanning_service.lib.utils.logger import log

# Redis client for subscription tracking
redis_client = redis.Redis(
    host=getattr(settings, 'REDIS_HOST', 'localhost'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=getattr(settings, 'REDIS_DB', 0),
    decode_responses=True
)

def get_group_name(algorithm_id: str, frequency: str) -> str:
    """
    Generate standardized group name for WebSocket subscriptions.
    
    Args:
        algorithm_id: Scanner algorithm ID
        frequency: Trading frequency
        
    Returns:
        str: Standardized group name
    """
    return f"scanner_{algorithm_id}_{frequency}"

def can_publish_to_group(group_name: str) -> bool:
    """
    Check if there are active subscribers for a WebSocket group.
    
    Args:
        group_name: WebSocket group name
        
    Returns:
        bool: True if there are subscribers, False otherwise
    """
    try:
        # Check Redis for active subscribers
        redis_key = f"subs:{group_name}"
        count = redis_client.get(redis_key)
        count = int(count) if count else 0
        
        can_publish = count > 0
        log(f"WebSocket: can_publish_to_group({group_name}) - Redis count: {count}, can_publish: {can_publish}", level="info")
        
        if not can_publish:
            log(f"WebSocket: No subscribers found for group '{group_name}' - messages will be skipped", level="warning")
        
        return can_publish
        
    except Exception as e:
        log(f"Error checking subscribers for {group_name}: {str(e)}", level="error")
        return False

async def publish_scanner_update_async(algorithm_id: str, frequency: str, update_data: Dict[str, Any]) -> bool:
    """
    Asynchronously publish scanner update to WebSocket subscribers.
    
    Args:
        algorithm_id: Scanner algorithm ID
        frequency: Trading frequency  
        update_data: Update data to publish
        
    Returns:
        bool: True if published successfully, False otherwise
    """
    try:
        group_name = get_group_name(algorithm_id, frequency)
        
        # Check if there are subscribers before publishing
        if not can_publish_to_group(group_name):
            log(f"No active subscribers for {group_name}, skipping publish", level="debug")
            return False
        
        # Get channel layer and publish
        channel_layer = get_channel_layer()
        if not channel_layer:
            log(f"No channel layer available for WebSocket publishing", level="error")
            return False
        
        await channel_layer.group_send(
            group_name,
            {
                'type': 'scanner_update',
                'data': update_data
            }
        )
        
        log(f"Published scanner update to {group_name}", level="info")
        return True
        
    except Exception as e:
        log(f"Error publishing to {group_name}: {str(e)}", level="error")
        return False

def run_async_in_thread(coro):
    """
    Run an async coroutine in a separate thread with proper event loop management.
    
    Args:
        coro: Coroutine to run
        
    Returns:
        Any: Result of the coroutine
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, we need to run in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=30)
        else:
            # Loop exists but not running, we can use it
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create a new one
        try:
            return asyncio.run(coro)
        except Exception as e:
            log(f"Error in event loop execution: {str(e)}", level="error")
            return False
    except Exception as e:
        log(f"Unexpected error in async execution: {str(e)}", level="error")
        return False
    finally:
        # Clean up any pending tasks
        try:
            pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
            if pending_tasks:
                log(f"Canceling {len(pending_tasks)} pending tasks before loop closure", level="debug")
                for task in pending_tasks:
                    task.cancel()
                
                # Wait for tasks to complete cancellation
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
                    
        except Exception as cleanup_error:
            log(f"Error during task cleanup: {str(cleanup_error)}", level="error")

def publish_scanner_update_sync(algorithm_id: str, frequency: str, update_data: Dict[str, Any]) -> bool:
    """
    Synchronously publish scanner update to WebSocket subscribers.
    This is a wrapper around the async function for use in synchronous contexts.
    
    Args:
        algorithm_id: Scanner algorithm ID
        frequency: Trading frequency
        update_data: Update data to publish
        
    Returns:
        bool: True if published successfully, False otherwise
    """
    try:
        coro = publish_scanner_update_async(algorithm_id, frequency, update_data)
        result = run_async_in_thread(coro)
        return bool(result)
        
    except asyncio.TimeoutError:
        log("WebSocket publish operation timed out", level="error")
        return False
    except Exception as e:
        log(f"Error in publish_scanner_update_sync: {str(e)}", level="error")
        return False

class ScannerWebSocketPublisher:
    """
    Publisher class for scanner WebSocket updates with automatic subscriber checking.
    """
    
    def __init__(self, algorithm_id: str, frequency: str):
        """
        Initialize publisher for specific algorithm and frequency.
        
        Args:
            algorithm_id: Scanner algorithm ID
            frequency: Trading frequency
        """
        self.algorithm_id = algorithm_id
        self.frequency = frequency
        self.group_name = get_group_name(algorithm_id, frequency)
        
        log(f"Scanner WebSocket publisher initialized for {self.group_name}", level="info")
    
    def can_publish(self) -> bool:
        """
        Check if there are active subscribers for this publisher's group.
        
        Returns:
            bool: True if there are subscribers, False otherwise
        """
        return can_publish_to_group(self.group_name)
    
    async def publish_async(self, update_data: Dict[str, Any]) -> bool:
        """
        Asynchronously publish update data.
        
        Args:
            update_data: Data to publish
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        return await publish_scanner_update_async(self.algorithm_id, self.frequency, update_data)
    
    def publish(self, update_data: Dict[str, Any]) -> bool:
        """
        Synchronously publish update data.
        
        Args:
            update_data: Data to publish
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        # Quick check for subscribers before attempting async operation
        if not self.can_publish():
            log(f"No subscribers for {self.group_name}, skipping update", level="debug")
            return False
        
        try:
            result = publish_scanner_update_sync(self.algorithm_id, self.frequency, update_data)
            
            if result:
                log(f"Published scanner update for {self.group_name}", level="info")
            else:
                log(f"Failed to publish scanner update for {self.group_name}", level="warning")
            
            return result
            
        except Exception as e:
            log(f"Error publishing scanner update: {str(e)}", level="error")
            return False

# Utility functions for backward compatibility
def validate_group_name(group_name: str) -> bool:
    """
    Validate WebSocket group name format.
    
    Args:
        group_name: Group name to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not group_name:
        return False
    
    # Expected format: scanner_{algorithm_id}_{frequency}
    parts = group_name.split('_')
    if len(parts) != 3 or parts[0] != 'scanner':
        log(f"Invalid group name format: {group_name}", level="warning")
        return False
    
    return True

def extract_algorithm_and_frequency(group_name: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract algorithm ID and frequency from group name.
    
    Args:
        group_name: WebSocket group name
        
    Returns:
        tuple: (algorithm_id, frequency) or (None, None) if invalid
    """
    if not validate_group_name(group_name):
        return None, None
    
    parts = group_name.split('_')
    return parts[1], parts[2] 