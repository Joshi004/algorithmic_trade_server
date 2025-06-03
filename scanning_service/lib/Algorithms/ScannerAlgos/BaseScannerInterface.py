"""
Base Scanner Interface for the scanning service.
Defines the standardized event format that all scanner algorithms must follow.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseScannerInterface(ABC):
    """
    Abstract base class for all scanner algorithms.
    Ensures consistent event format across different scanning algorithms.
    """
    
    # Standardized field names for eligible instrument events
    STANDARD_EVENT_FIELDS = [
        'instrument_id',      # Required: Unique identifier for the instrument
        'trading_symbol',     # Required: Trading symbol (e.g., "RELIANCE")
        'support_price',      # Optional: Support price level (None if not applicable)
        'resistance_price',   # Optional: Resistance price level (None if not applicable)
        'required_action',    # Optional: "buy", "sell", or None
        'market_price'        # Required: Current market price
    ]
    
    def __init__(self):
        """
        Initialize the scanner with minimal setup.
        Use configure() method to set up the scanner with required parameters.
        """
        self.trade_frequency = None
        self.user_id = None
        self.trade_session_id = None
        self._configured = False
    
    @abstractmethod
    def configure(self, trade_freq: str, user_id: str = None, trade_session_id: str = None, **kwargs):
        """
        Configure the scanner with required parameters and dependencies.
        Each scanner implementation can accept different configuration parameters.
        
        Args:
            trade_freq: Trading frequency (e.g., "5minute")
            user_id: User ID for the scanner
            trade_session_id: Trade session ID for event correlation
            **kwargs: Additional scanner-specific configuration parameters
        """
        self.trade_frequency = trade_freq
        self.user_id = user_id
        self.trade_session_id = trade_session_id
        self._configured = True
    
    def is_configured(self) -> bool:
        """
        Check if the scanner has been properly configured.
        
        Returns:
            bool: True if configured, False otherwise
        """
        return self._configured
    
    def _ensure_configured(self):
        """
        Ensure the scanner is configured before running operations.
        
        Raises:
            RuntimeError: If scanner is not configured
        """
        if not self.is_configured():
            raise RuntimeError(f"Scanner {self.__class__.__name__} must be configured before use. Call configure() first.")
    
    @abstractmethod
    def is_eligible(self, symbol: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if an instrument is eligible for trading based on the scanner's criteria.
        
        Args:
            symbol: Trading symbol to check
            
        Returns:
            tuple: (is_eligible: bool, eligibility_data: dict)
        """
        pass
    
    @abstractmethod
    def fetch_instrument_tokens_and_start_tracking(self, user_id: str, dummy: bool):
        """
        Start the scanner to fetch instruments and begin tracking.
        
        Args:
            user_id: User ID
            dummy: Whether this is a dummy/paper trading session
        """
        pass
    
    @abstractmethod
    def stop_scanning(self):
        """
        Stop the scanner gracefully.
        """
        pass
    
    def format_eligible_instrument(self, instrument_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format instrument data according to the standardized event format.
        All scanners must use this method to ensure consistent event structure.
        
        Args:
            instrument_data: Raw instrument data from the scanner
            
        Returns:
            dict: Standardized instrument data with required fields
            
        Required fields in input:
            - instrument_id: str or int
            - trading_symbol: str
            - market_price: float
            
        Optional fields (set to None if not available):
            - support_price: float or None
            - resistance_price: float or None
            - required_action: str ("buy", "sell") or None
        """
        # Validate required fields
        required_fields = ['instrument_id', 'trading_symbol', 'market_price']
        for field in required_fields:
            if field not in instrument_data:
                raise ValueError(f"Missing required field '{field}' in instrument data")
        
        # Create standardized format
        standardized_data = {
            'instrument_id': str(instrument_data['instrument_id']),
            'trading_symbol': str(instrument_data['trading_symbol']),
            'support_price': instrument_data.get('support_price'),
            'resistance_price': instrument_data.get('resistance_price'),
            'required_action': instrument_data.get('required_action'),
            'market_price': float(instrument_data['market_price'])
        }
        
        # Ensure None values for missing optional fields
        for field in ['support_price', 'resistance_price', 'required_action']:
            if standardized_data[field] is None:
                standardized_data[field] = None
            elif field in ['support_price', 'resistance_price'] and standardized_data[field] is not None:
                standardized_data[field] = float(standardized_data[field])
        
        return standardized_data
    
    def get_standard_event_format(self) -> Dict[str, str]:
        """
        Get the standard event format documentation.
        
        Returns:
            dict: Field descriptions for the standard format
        """
        return {
            'instrument_id': 'Unique identifier for the instrument (string)',
            'trading_symbol': 'Trading symbol like RELIANCE, HDFCBANK (string)',
            'support_price': 'Support price level or None if not applicable (float|None)',
            'resistance_price': 'Resistance price level or None if not applicable (float|None)',
            'required_action': '"buy", "sell", or None based on analysis (string|None)',
            'market_price': 'Current market price (float)'
        } 