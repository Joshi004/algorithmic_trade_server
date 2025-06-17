"""
WebSocket Publisher Utility for Scanning Service

This module provides functionality for the scanning service to publish
scanner updates to connected WebSocket clients via the gateway service.
Completely independent from ats_gateway to avoid tight coupling.
"""

import sys
import os
import django
import asyncio
import redis
import logging

# Add the project root to Python path and configure Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')

try:
    django.setup()
except RuntimeError:
    # Django is already configured
    pass

from django.conf import settings
from channels.layers import get_channel_layer

# Get logger
logger = logging.getLogger(__name__)

# Redis connection for subscription tracking
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

# Get the default channel layer
channel_layer = get_channel_layer()

def get_group_name(algorithm_id, frequency):
    """
    Generate group name using convention: scanner_<algorithm>_<frequency>
    Example: scanner_2_5min
    """
    return f"scanner_{algorithm_id}_{frequency}"

def get_group_subscription_count(group_name):
    """
    Get current subscriber count for a group
    Returns 0 if key doesn't exist
    """
    redis_key = f"subs:{group_name}"
    count = redis_client.get(redis_key)
    return int(count) if count else 0

def can_publish_to_group(group_name):
    """
    Check if there are active subscribers for a group
    Returns True if count > 0, False otherwise
    """
    count = get_group_subscription_count(group_name)
    return count > 0

async def publish_scanner_update(algorithm_id, frequency, data):
    """
    Publish a scanner update to the appropriate group
    Only publishes if there are active subscribers
    
    Args:
        algorithm_id: The scanner algorithm ID
        frequency: The scanning frequency (e.g., '5min')
        data: The scanner update data to send
    """
    # Generate group name using the same convention
    group_name = get_group_name(algorithm_id, frequency)
    
    # Check if there are active subscribers
    if not can_publish_to_group(group_name):
        logger.debug(f"No active subscribers for {group_name}, skipping publish")
        return False
    
    try:
        # Send message to the group
        await channel_layer.group_send(
            group_name,
            {
                'type': 'scanner_update',  # This calls the scanner_update method in the consumer
                'data': data
            }
        )
        
        logger.info(f"Published scanner update to {group_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error publishing to {group_name}: {str(e)}")
        return False

def publish_scanner_update_sync(algorithm_id, frequency, data):
    """
    Synchronous wrapper for publish_scanner_update
    Useful for scanner services that run in sync context
    """
    try:
        # Create new event loop if none exists
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        publish_scanner_update(algorithm_id, frequency, data)
    )

def get_active_scanner_groups():
    """
    Get all scanner groups that have active subscribers
    Returns a list of group names
    """
    # Get all subscription keys
    pattern = "subs:scanner_*"
    keys = redis_client.keys(pattern)
    
    active_groups = []
    for key in keys:
        count = redis_client.get(key)
        if count and int(count) > 0:
            # Extract group name from Redis key (remove 'subs:' prefix)
            group_name = key[5:]  # Remove 'subs:' prefix
            active_groups.append(group_name)
    
    return active_groups

class ScannerWebSocketPublisher:
    """
    Publisher class for scanner services to send real-time updates
    to WebSocket clients through the gateway service
    """
    
    def __init__(self, algorithm_id, frequency):
        """
        Initialize publisher for a specific algorithm and frequency
        
        Args:
            algorithm_id: The scanner algorithm ID
            frequency: The scanning frequency (e.g., '5min', '1min')
        """
        self.algorithm_id = algorithm_id
        self.frequency = frequency
        self.group_name = get_group_name(algorithm_id, frequency)
        logger.info(f"Scanner WebSocket publisher initialized for {self.group_name}")
    
    def has_subscribers(self):
        """
        Check if there are active subscribers for this scanner
        Returns True if there are subscribers, False otherwise
        """
        return can_publish_to_group(self.group_name)
    
    def publish_update(self, update_data):
        """
        Publish a scanner update to connected WebSocket clients
        Only publishes if there are active subscribers
        
        Args:
            update_data: Dictionary containing the scanner update data
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        if not self.has_subscribers():
            logger.debug(f"No subscribers for {self.group_name}, skipping update")
            return False
        
        try:
            # Add metadata to the update
            message = {
                'type': 'scanner_update',
                'algorithm_id': self.algorithm_id,
                'frequency': self.frequency,
                'group_name': self.group_name,
                'timestamp': update_data.get('timestamp'),
                'data': update_data
            }
            
            # Publish the update
            success = publish_scanner_update_sync(
                self.algorithm_id,
                self.frequency,
                message
            )
            
            if success:
                logger.info(f"Published scanner update for {self.group_name}")
            else:
                logger.warning(f"Failed to publish scanner update for {self.group_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing scanner update: {str(e)}")
            return False
    
    def publish_scanner_status(self, status, message=None):
        """
        Publish scanner status updates (started, stopped, error, etc.)
        
        Args:
            status: Status string ('started', 'stopped', 'error', 'processing')
            message: Optional status message
        """
        status_data = {
            'type': 'scanner_status',
            'algorithm_id': self.algorithm_id,
            'frequency': self.frequency,
            'group_name': self.group_name,
            'status': status,
            'message': message,
            'timestamp': None  # Will be set by the calling service
        }
        
        return self.publish_update(status_data)
    
    def publish_scan_result(self, result_data):
        """
        Publish scan results to subscribers
        
        Args:
            result_data: Dictionary containing scan results
        """
        scan_data = {
            'type': 'scan_result',
            'algorithm_id': self.algorithm_id,
            'frequency': self.frequency,
            'group_name': self.group_name,
            'result': result_data,
            'timestamp': result_data.get('timestamp')
        }
        
        return self.publish_update(scan_data)

def get_all_active_scanners():
    """
    Get list of all active scanner groups that have subscribers
    Useful for scanning service to know which scanners to run
    
    Returns:
        list: List of tuples (algorithm_id, frequency) for active scanners
    """
    active_groups = get_active_scanner_groups()
    active_scanners = []
    
    for group_name in active_groups:
        # Parse group name: scanner_<algorithm>_<frequency>
        if group_name.startswith('scanner_'):
            parts = group_name[8:].split('_', 1)  # Remove 'scanner_' prefix
            if len(parts) >= 2:
                algorithm_id = parts[0]
                frequency = parts[1]
                active_scanners.append((algorithm_id, frequency))
            else:
                logger.warning(f"Invalid group name format: {group_name}")
    
    return active_scanners

def should_run_scanner(algorithm_id, frequency):
    """
    Check if a scanner should be running based on subscriber count
    
    Args:
        algorithm_id: The scanner algorithm ID
        frequency: The scanning frequency
        
    Returns:
        bool: True if scanner should run, False otherwise
    """
    group_name = get_group_name(algorithm_id, frequency)
    return can_publish_to_group(group_name) 