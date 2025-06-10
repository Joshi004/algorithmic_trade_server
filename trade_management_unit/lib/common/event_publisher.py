import uuid
from datetime import datetime
from django.conf import settings
from trade_management_unit.lib.common.Utils.redis_stream_client import get_redis_stream_client
from trade_management_unit.lib.common.Utils.custome_logger import log
from trade_management_unit.lib.common.Utils.Utils import current_ist


class TradeSessionEventPublisher:
    """
    Event publisher for trade session related events.
    Handles formatting and publishing of events to Redis streams.
    """
    
    def __init__(self):
        """Initialize the event publisher"""
        # Get stream names from Django settings
        self.scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        self.redis_client = get_redis_stream_client()
    
    def publish_trade_session_initiated(self, trade_session_obj, message="New session created"):
        """
        Publish trade session initiation event to Redis stream.
        
        Args:
            trade_session_obj: TradeSession model instance
            message (str): Creation message context
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Only publish for new session creation, not existing sessions
            if message != "New session created":
                log(f"Skipping event publish for trade session {trade_session_obj.id}: {message}")
                return True
            
            # Format event data
            event_data = self._format_trade_session_event(trade_session_obj)
            
            # Publish to Redis stream
            success = self.redis_client.publish_to_stream(
                self.scanning_queue, 
                event_data
            )
            
            if success:
                log(f"Published trade session initiation event for session {trade_session_obj.id}")
            else:
                log(f"Failed to publish trade session initiation event for session {trade_session_obj.id}", level="error")
            
            return success
            
        except Exception as e:
            log(f"Error publishing trade session initiation event for session {trade_session_obj.id}: {str(e)}", level="error")
            return False
    
    def _format_trade_session_event(self, trade_session_obj):
        """
        Format trade session data into flat event structure.
        
        Args:
            trade_session_obj: TradeSession model instance
            
        Returns:
            dict: Flat event data without nesting
        """
        try:
            # Get current timestamp in IST
            current_time = current_ist()
            
            # Format the event payload as completely flat structure
            event_data = {
                "event_id": str(uuid.uuid4()),
                "event_type": "trade_session_initiated",
                "timestamp": current_time.isoformat(),
                "trade_session_id": trade_session_obj.id,
                "user_id": str(trade_session_obj.user_id.public_id),
                "scanning_algorithm_id": trade_session_obj.scanning_algorithm.id,
                "initiation_algorithm_id": trade_session_obj.initiation_algorithm.id,
                "termination_algorithm_id": trade_session_obj.termination_algorithm.id,
                "trading_frequency": trade_session_obj.trading_frequency,
                "is_dummy": trade_session_obj.dummy,
                "session_status": trade_session_obj.status,
                "started_at": trade_session_obj.started_at.isoformat() if trade_session_obj.started_at else None
            }
            
            log(f"Formatted flat event data for trade session {trade_session_obj.id}")
            return event_data
            
        except Exception as e:
            log(f"Error formatting trade session event data: {str(e)}", level="error")
            raise
    
    def health_check(self):
        """
        Check if the event publisher is healthy (Redis connection).
        
        Returns:
            bool: True if healthy, False otherwise
        """
        return self.redis_client.health_check()


# Singleton instance for reuse across the application
_event_publisher_instance = None

def get_trade_session_event_publisher():
    """
    Get singleton trade session event publisher instance.
    
    Returns:
        TradeSessionEventPublisher: Event publisher instance
    """
    global _event_publisher_instance
    if _event_publisher_instance is None:
        _event_publisher_instance = TradeSessionEventPublisher()
    return _event_publisher_instance 