"""
Event publisher for the scanning service.
Publishes scanner-related events to Redis streams for consumption by other services.
"""
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from scanning_service.lib.utils.logger import log
from scanning_service.lib.utils.common import current_ist
from .publisher_client import get_publisher_client
from ..utils import prepare_for_redis_stream


class ScanningEventPublisher:
    """
    Publishes scanning-related events to Redis streams.
    Uses optimized publisher Redis client for fast, non-blocking operations.
    """
    
    def __init__(self):
        """Initialize the event publisher with Redis client and stream names"""
        self.publisher_client = get_publisher_client()
        self.config = self.publisher_client.config
        
        # Stream names from configuration
        self.initiation_queue_stream = self.config.initiation_queue_stream
        self.scanner_status_stream = self.config.scanner_status_stream
        
        # Ensure Redis connection
        self._ensure_redis_connection()
    
    def _ensure_redis_connection(self):
        """Ensure Redis connection is available"""
        if not self.publisher_client.health_check():
            log("Failed to establish Redis connection in event publisher", level="error")
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        return f"evt_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    def publish_eligible_instrument(
        self,
        trade_session_id: str,
        instrument_data: Dict[str, Any],
        scanner_type: str = None
    ) -> Optional[str]:
        """
        Publish an eligible instrument found by scanner using standardized format.
        
        Args:
            trade_session_id: Trade session ID
            instrument_data: Dictionary containing standardized instrument details
            scanner_type: Type of scanner (required parameter)
            
        Returns:
            Message ID if successful, None otherwise
            
        Expected instrument_data format:
        {
            "instrument_id": "738561",
            "trading_symbol": "RELIANCE", 
            "support_price": 2450.50,
            "resistance_price": 2500.75,
            "required_action": "buy",
            "market_price": 2475.30
        }
        """
        try:
            # Validate required parameter
            if not scanner_type:
                log("Scanner type is required for publishing eligible instrument", level="error")
                return None
                
            # Create standardized event data format
            event_data = {
                'event_id': self._generate_event_id(),
                'event_type': 'eligible_instrument_found',
                'trade_session_id': trade_session_id,
                'timestamp': current_ist().isoformat(),
                'instrument_id': instrument_data.get('instrument_id'),
                'trading_symbol': instrument_data.get('trading_symbol'),
                'support_price': instrument_data.get('support_price'),
                'resistance_price': instrument_data.get('resistance_price'),
                'required_action': instrument_data.get('required_action'),
                'market_price': instrument_data.get('market_price'),
                'scanner_type': scanner_type
            }
            
            # Flatten the data for Redis stream
            flat_data = prepare_for_redis_stream(event_data)
            
            # Publish to stream using optimized publisher client
            message_id = self.publisher_client.publish_to_stream(
                self.initiation_queue_stream,
                flat_data
            )
            
            if message_id:
                log(f"Published eligible instrument event: {message_id} for {instrument_data.get('trading_symbol')}")
            
            return message_id
            
        except Exception as e:
            log(f"Failed to publish eligible instrument event: {str(e)}", level="error")
            return None
    
    def publish_scanner_status(
        self,
        user_id: str,
        trade_session_id: str,
        scanner_type: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Publish scanner status update.
        
        Args:
            user_id: User ID
            trade_session_id: Trade session ID
            scanner_type: Type of scanner
            status: Scanner status (started, running, stopped, error)
            details: Additional status details
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            # Create event data
            event_data = {
                'event_id': self._generate_event_id(),
                'event_type': 'scanner_status_update',
                'user_id': user_id,
                'trade_session_id': trade_session_id,
                'scanner_type': scanner_type,
                'status': status,
                'timestamp': current_ist().isoformat()
            }
            
            if details:
                event_data['details'] = details
            
            # Flatten the data for Redis stream
            flat_data = prepare_for_redis_stream(event_data)
            
            # Publish to stream using optimized publisher client
            message_id = self.publisher_client.publish_to_stream(
                self.scanner_status_stream,
                flat_data
            )
            
            if message_id:
                log(f"Published scanner status event: {message_id} - {scanner_type} {status}")
            
            return message_id
            
        except Exception as e:
            log(f"Failed to publish scanner status event: {str(e)}", level="error")
            return None
    
    def publish_batch_eligible_instruments(
        self,
        trade_session_id: str,
        instruments: List[Dict[str, Any]],
        scanner_type: str = None
    ) -> int:
        """
        Publish multiple eligible instruments in a batch operation.
        
        Args:
            trade_session_id: Trade session ID
            instruments: List of instrument data dictionaries
            scanner_type: Type of scanner (required parameter)
            
        Returns:
            Number of successfully published instruments
        """
        if not instruments:
            return 0
        
        # Validate required parameter
        if not scanner_type:
            log("Scanner type is required for batch publishing eligible instruments", level="error")
            return 0

        try:
            # Prepare batch data
            batch_data = []
            
            for instrument_data in instruments:
                event_data = {
                    'event_id': self._generate_event_id(),
                    'event_type': 'eligible_instrument_found',
                    'trade_session_id': trade_session_id,
                    'timestamp': current_ist().isoformat(),
                    'instrument_id': instrument_data.get('instrument_id'),
                    'trading_symbol': instrument_data.get('trading_symbol'),
                    'support_price': instrument_data.get('support_price'),
                    'resistance_price': instrument_data.get('resistance_price'),
                    'required_action': instrument_data.get('required_action'),
                    'market_price': instrument_data.get('market_price'),
                    'scanner_type': scanner_type
                }
                
                # Flatten the data for Redis stream
                flat_data = prepare_for_redis_stream(event_data)
                batch_data.append(flat_data)
            
            # Publish batch using optimized publisher client
            published_count = self.publisher_client.publish_batch_to_stream(
                self.initiation_queue_stream,
                batch_data
            )
            
            log(f"Published {published_count}/{len(instruments)} eligible instruments in batch")
            return published_count
            
        except Exception as e:
            log(f"Failed to publish batch eligible instruments: {str(e)}", level="error")
            return 0
    



# Singleton instance for event publisher
_event_publisher = None

def get_scanning_event_publisher() -> ScanningEventPublisher:
    """
    Get or create singleton scanning event publisher instance
    
    Returns:
        ScanningEventPublisher instance
    """
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = ScanningEventPublisher()
    return _event_publisher 