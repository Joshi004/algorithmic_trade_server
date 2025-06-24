"""
UDTS State Manager Implementation.
Manages state persistence for UDTS scanners using Redis.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from scanning_service.lib.utils.logger import log
from scanning_service.lib.utils.redis import get_publisher_client
from scanning_service.lib.utils.common import current_ist
from .interfaces import StateManagerInterface
from .config import StateManagementConfig


class UDTSStateManager(StateManagerInterface):
    """
    State manager implementation for UDTS scanners.
    Stores state in Redis with configurable TTL and key format.
    """
    
    def __init__(self, algorithm_type: str, frequency: str, ttl_hours: float = None):
        """
        Initialize UDTS State Manager.
        
        Args:
            algorithm_type: Type of algorithm (e.g., "udts")
            frequency: Trading frequency (e.g., "5-minute")
            ttl_hours: Time to live in hours (uses config default if None)
        """
        self.algorithm_type = algorithm_type
        self.frequency = frequency
        self.ttl_seconds = StateManagementConfig.get_state_ttl_seconds(ttl_hours)
        self.redis_client = get_publisher_client()
        
        # Redis key format: scanner:state:{algorithm_type}__{frequency}
        self.state_key = f"{StateManagementConfig.STATE_KEY_PREFIX}{algorithm_type}__{frequency}"
        
    def save_progress(self, current_index: int, total_instruments: int, 
                     last_processed_symbol: str, scan_cycle: int,
                     cycle_start_time: datetime) -> bool:
        """
        Save current scanning progress to Redis.
        
        Args:
            current_index: Current index in the instrument list
            total_instruments: Total number of instruments being scanned
            last_processed_symbol: Symbol of the last processed instrument
            scan_cycle: Current scan cycle number
            cycle_start_time: When the current cycle started
            
        Returns:
            bool: True if progress saved successfully, False otherwise
        """
        try:
            client = self.redis_client.get_client()
            if client is None:
                log("Redis client unavailable, cannot save progress", level="error")
                return False
            
            # Prepare state data
            state_data = {
                'current_index': current_index,
                'total_instruments': total_instruments,
                'last_processed_symbol': last_processed_symbol,
                'scan_cycle': scan_cycle,
                'cycle_start_time': cycle_start_time.isoformat(),
                'last_update_time': current_ist().isoformat()
            }
            
            # Use pipeline for atomic operation
            with client.pipeline() as pipe:
                pipe.hset(self.state_key, mapping=state_data)
                pipe.expire(self.state_key, self.ttl_seconds)
                pipe.execute()
            
            log(f"State saved for {self.algorithm_type}_{self.frequency}: index {current_index}/{total_instruments}")
            return True
            
        except Exception as e:
            log(f"Error saving progress for {self.state_key}: {str(e)}", level="error")
            return False
    
    def get_progress(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve current scanning progress from Redis.
        
        Returns:
            Optional[Dict]: Progress data if exists, None otherwise
        """
        try:
            client = self.redis_client.get_client()
            if client is None:
                log("Redis client unavailable, cannot get progress", level="error")
                return None
            
            # Get all hash fields
            state_data = client.hgetall(self.state_key)
            
            if not state_data:
                log(f"No progress state found for {self.state_key}")
                return None
            
            # Convert string values back to appropriate types
            progress = {
                'current_index': int(state_data.get('current_index', 0)),
                'total_instruments': int(state_data.get('total_instruments', 0)),
                'last_processed_symbol': state_data.get('last_processed_symbol', ''),
                'scan_cycle': int(state_data.get('scan_cycle', 0)),
                'cycle_start_time': datetime.fromisoformat(state_data.get('cycle_start_time')),
                'last_update_time': datetime.fromisoformat(state_data.get('last_update_time'))
            }
            
            log(f"Retrieved progress for {self.state_key}: index {progress['current_index']}/{progress['total_instruments']}")
            return progress
            
        except Exception as e:
            log(f"Error getting progress for {self.state_key}: {str(e)}", level="error")
            return None
    
    def clear_state(self) -> bool:
        """
        Clear all state data for this scanner.
        
        Returns:
            bool: True if state cleared successfully, False otherwise
        """
        try:
            client = self.redis_client.get_client()
            if client is None:
                log("Redis client unavailable, cannot clear state", level="error")
                return False
            
            # Clear only the state key
            deleted_count = client.delete(self.state_key)
            
            log(f"Cleared state for {self.state_key} - deleted {deleted_count} keys")
            return True
            
        except Exception as e:
            log(f"Error clearing state for {self.state_key}: {str(e)}", level="error")
            return False 