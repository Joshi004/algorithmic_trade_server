"""
State Manager Factory for Scanner Services.
Provides factory pattern implementation to get appropriate StateManager based on scanner type.
"""

from typing import Optional
from scanning_service.lib.utils.logger import log
from .interfaces import StateManagerInterface
from .udts_state_manager import UDTSStateManager


class StateManagerFactory:
    """
    Factory class for creating StateManager instances based on scanner type.
    Ensures consistent creation and configuration of state managers.
    """
    
    # Mapping of scanner types to their respective state manager classes
    STATE_MANAGER_MAP = {
        'udts': UDTSStateManager,
        # Future scanner types can be added here
        # 'rsi_divergence': RSIStateManager,
        # 'breakout_scanner': BreakoutStateManager,
        # 'momentum_surge': MomentumStateManager
    }
    
    @classmethod
    def create_state_manager(cls, scanner_type: str, algorithm_type: str, 
                           frequency: str, **kwargs) -> Optional[StateManagerInterface]:
        """
        Create a StateManager instance based on scanner type.
        
        Args:
            scanner_type: Type of scanner (e.g., "udts", "rsi_divergence")
            algorithm_type: Algorithm type identifier (e.g., "udts")
            frequency: Trading frequency (e.g., "5-minute")
            **kwargs: Additional configuration parameters (e.g., ttl_hours)
            
        Returns:
            StateManagerInterface instance or None if scanner type not supported
        """
        scanner_type_lower = scanner_type.lower()
        
        if scanner_type_lower not in cls.STATE_MANAGER_MAP:
            log(f"StateManager not available for scanner type: {scanner_type}", level="warning")
            return None
        
        try:
            state_manager_class = cls.STATE_MANAGER_MAP[scanner_type_lower]
            
            # Create state manager instance with provided parameters
            state_manager = state_manager_class(
                algorithm_type=algorithm_type,
                frequency=frequency,
                **kwargs
            )
            
            log(f"Created StateManager for {scanner_type} scanner: {algorithm_type}_{frequency}")
            return state_manager
            
        except Exception as e:
            log(f"Error creating StateManager for {scanner_type}: {str(e)}", level="error")
            return None
    
    @classmethod
    def get_supported_scanner_types(cls) -> list:
        """
        Get list of supported scanner types.
        
        Returns:
            List of supported scanner type strings
        """
        return list(cls.STATE_MANAGER_MAP.keys())
    
    @classmethod
    def is_scanner_type_supported(cls, scanner_type: str) -> bool:
        """
        Check if a scanner type is supported.
        
        Args:
            scanner_type: Type of scanner to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        return scanner_type.lower() in cls.STATE_MANAGER_MAP 