"""
Event publisher for the scanning service.
Publishes scanner-related events to Redis streams for consumption by other services.
"""
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from django.conf import settings
from scanning_service.lib.utils.redis_client import get_redis_client
from scanning_service.lib.utils.logger import log
from scanning_service.lib.utils.common import current_ist


class ScanningEventPublisher:
    """
    Publishes scanning-related events to Redis streams.
    """
    
    def __init__(self):
        """Initialize the event publisher."""
        # Get stream names from Django settings
        self.initiation_queue_stream = getattr(settings, 'REDIS_STREAM_INITIATION_QUEUE', 'initiation_queue')
        self.scanner_status_stream = getattr(settings, 'REDIS_STREAM_SCANNER_STATUS', 'scanner_status_stream')
        
        self.redis_client = None
        self._ensure_redis_connection()
    
    def _ensure_redis_connection(self):
        """Ensure Redis client is connected."""
        try:
            self.redis_client = get_redis_client()
        except Exception as e:
            log(f"Failed to get Redis client in event publisher: {str(e)}", level="error")
            self.redis_client = None
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        return f"evt_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    def _flatten_dict(self, data: Dict[str, Any], parent_key: str = '') -> Dict[str, str]:
        """
        Flatten nested dictionary for Redis stream.
        Redis streams require flat key-value pairs.
        
        Args:
            data: Dictionary to flatten
            parent_key: Parent key for nested items
            
        Returns:
            Flattened dictionary with string values
        """
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}_{key}" if parent_key else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                items.extend(self._flatten_dict(value, new_key).items())
            elif isinstance(value, (list, tuple)):
                # Convert lists to JSON strings
                items.append((new_key, json.dumps(value)))
            elif value is None:
                # Convert None to empty string
                items.append((new_key, ''))
            else:
                # Convert everything else to string
                items.append((new_key, str(value)))
        
        return dict(items)
    
    def publish_eligible_instrument(
        self,
        trade_session_id: str,
        instrument_data: Dict[str, Any],
        scanner_type: str = "udts"
    ) -> Optional[str]:
        """
        Publish an eligible instrument found by scanner using standardized format.
        
        Args:
            trade_session_id: Trade session ID
            instrument_data: Dictionary containing standardized instrument details
            scanner_type: Type of scanner (default: "udts")
            
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
        if not self.redis_client:
            log("Redis client not available, cannot publish event", level="error")
            return None
        
        try:
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
                'market_price': instrument_data.get('market_price')
            }
            
            # Flatten the data for Redis stream
            flat_data = self._flatten_dict(event_data)
            
            # Publish to stream
            message_id = self.redis_client.xadd(
                self.initiation_queue_stream,
                flat_data
            )
            
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
        if not self.redis_client:
            log("Redis client not available, cannot publish event", level="error")
            return None
        
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
            flat_data = self._flatten_dict(event_data)
            
            # Publish to stream
            message_id = self.redis_client.xadd(
                self.scanner_status_stream,
                flat_data
            )
            
            log(f"Published scanner status event: {message_id} - {scanner_type} {status}")
            return message_id
            
        except Exception as e:
            log(f"Failed to publish scanner status event: {str(e)}", level="error")
            return None
    
    def publish_batch_eligible_instruments(
        self,
        trade_session_id: str,
        instruments: list,
        scanner_type: str = "udts"
    ) -> int:
        """
        Publish multiple eligible instruments in batch using standardized format.
        
        Args:
            trade_session_id: Trade session ID
            instruments: List of instrument data dictionaries in standardized format
            scanner_type: Type of scanner
            
        Returns:
            Number of successfully published events
        """
        published_count = 0
        
        for instrument in instruments:
            if self.publish_eligible_instrument(
                trade_session_id,
                instrument,
                scanner_type
            ):
                published_count += 1
        
        log(f"Published {published_count}/{len(instruments)} eligible instruments")
        return published_count


# Singleton instance
_event_publisher = None

def get_scanning_event_publisher() -> ScanningEventPublisher:
    """
    Get or create a singleton ScanningEventPublisher instance.
    
    Returns:
        ScanningEventPublisher: Event publisher instance
    """
    global _event_publisher
    
    if _event_publisher is None:
        _event_publisher = ScanningEventPublisher()
    
    return _event_publisher 