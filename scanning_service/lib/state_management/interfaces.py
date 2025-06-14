"""
State Manager Interface for Scanner Services.
Defines the contract that all state managers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime


class StateManagerInterface(ABC):
    """
    Abstract interface for scanner state management.
    All state managers must implement these methods to ensure consistency.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_progress(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve current scanning progress from Redis.
        
        Returns:
            Optional[Dict]: Progress data if exists, None otherwise
                          Contains: current_index, total_instruments, last_processed_symbol,
                                  scan_cycle, cycle_start_time, last_update_time
        """
        pass
    
    @abstractmethod
    def clear_state(self) -> bool:
        """
        Clear all state data for this scanner.
        
        Returns:
            bool: True if state cleared successfully, False otherwise
        """
        pass 