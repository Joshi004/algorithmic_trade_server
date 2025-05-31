import json
import time
import redis
import os
from datetime import datetime
from typing import Dict, Any, Optional

from scanning_service.lib.utils.logger import log


class ScanningQueueConsumer:
    """
    Consumer for processing trade session scanning events from Redis stream.
    Reads from 'scanning_queue' stream and processes trade session events.
    """
    
    def __init__(self):
        """Initialize the consumer with Redis connection and configuration"""
        self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
        self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
        self.redis_db = 0
        self.stream_name = "scanning_queue"
        self.consumer_group = "scanning_service_group"
        self.consumer_name = f"scanning_consumer_{int(time.time())}"
        self.batch_size = 10
        self.timeout = 1000  # 1 second timeout
        
        self._client = None
        self._running = False
        
        log(f"Initialized ScanningQueueConsumer with consumer name: {self.consumer_name}")
    
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with proper configuration"""
        try:
            if self._client is None:
                self._client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    db=self.redis_db,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    decode_responses=True,
                    health_check_interval=30
                )
            return self._client
        except Exception as e:
            log(f"Failed to create Redis client: {str(e)}", level="error")
            return None
    
    def _ensure_consumer_group(self) -> bool:
        """Ensure the consumer group exists, create if it doesn't"""
        try:
            client = self._get_redis_client()
            if client is None:
                return False
            
            # Try to create the consumer group (from beginning of stream)
            try:
                client.xgroup_create(self.stream_name, self.consumer_group, id='0', mkstream=True)
                log(f"Created consumer group '{self.consumer_group}' for stream '{self.stream_name}'")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    log(f"Consumer group '{self.consumer_group}' already exists")
                else:
                    log(f"Error creating consumer group: {str(e)}", level="error")
                    return False
            
            return True
            
        except Exception as e:
            log(f"Error ensuring consumer group: {str(e)}", level="error")
            return False
    
    def _process_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process a single trade session scanning event.
        
        Args:
            event_data: The event data from Redis stream
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            # Extract event information
            event_id = event_data.get('event_id', 'unknown')
            event_type = event_data.get('event_type', 'unknown')
            trade_session_id = event_data.get('trade_session_id', 'unknown')
            user_id = event_data.get('user_id', 'unknown')
            timestamp = event_data.get('timestamp', 'unknown')
            
            log(f"Processing event {event_id}: {event_type} for trade session {trade_session_id}")
            
            # Basic event validation
            if event_type != 'trade_session_initiated':
                log(f"Skipping unknown event type: {event_type}", level="warning")
                return True
            
            # TODO: Implement actual business logic here
            # For now, just log the event details
            log(f"Successfully processed trade session scanning:")
            log(f"  - Event ID: {event_id}")
            log(f"  - Trade Session ID: {trade_session_id}")
            log(f"  - User ID: {user_id}")
            log(f"  - Timestamp: {timestamp}")
            log(f"  - Trading Frequency: {event_data.get('trading_frequency', 'unknown')}")
            log(f"  - Is Dummy: {event_data.get('is_dummy', 'unknown')}")
            log(f"  - Status: {event_data.get('session_status', 'unknown')}")
            
            return True
            
        except Exception as e:
            log(f"Error processing event: {str(e)}", level="error")
            return False
    
    def _unflatten_event_data(self, flattened_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert flattened Redis stream data back to nested structure.
        
        Args:
            flattened_data: Flattened data from Redis stream
            
        Returns:
            dict: Reconstructed nested data
        """
        result = {}
        
        for key, value in flattened_data.items():
            if '_' in key:
                # Handle nested keys (e.g., "algorithm_config_scanning_algorithm_id")
                parts = key.split('_')
                current = result
                
                # Navigate/create nested structure
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set the final value
                current[parts[-1]] = value
            else:
                # Direct key
                result[key] = value
        
        return result
    
    def start_consuming(self):
        """Start consuming messages from the scanning queue"""
        try:
            log("Starting ScanningQueueConsumer...")
            
            client = self._get_redis_client()
            if client is None:
                log("Failed to get Redis client, cannot start consumer", level="error")
                return
            
            # Test Redis connection
            client.ping()
            log("Redis connection established successfully")
            
            # Ensure consumer group exists
            if not self._ensure_consumer_group():
                log("Failed to ensure consumer group, cannot start consumer", level="error")
                return
            
            self._running = True
            log(f"Consumer started successfully, listening on stream '{self.stream_name}'")
            
            while self._running:
                try:
                    # Read messages from the stream
                    messages = client.xreadgroup(
                        self.consumer_group,
                        self.consumer_name,
                        {self.stream_name: '>'},
                        count=self.batch_size,
                        block=self.timeout
                    )
                    
                    if messages:
                        for stream, stream_messages in messages:
                            for message_id, fields in stream_messages:
                                try:
                                    # Unflatten the event data
                                    event_data = self._unflatten_event_data(fields)
                                    
                                    # Process the event
                                    success = self._process_event(event_data)
                                    
                                    if success:
                                        # Acknowledge the message
                                        client.xack(self.stream_name, self.consumer_group, message_id)
                                        log(f"Acknowledged message {message_id}")
                                    else:
                                        log(f"Failed to process message {message_id}, not acknowledging", level="error")
                                        
                                except Exception as e:
                                    log(f"Error processing message {message_id}: {str(e)}", level="error")
                    
                except redis.ConnectionError as e:
                    log(f"Redis connection error: {str(e)}", level="error")
                    time.sleep(5)  # Wait before retry
                except redis.TimeoutError:
                    # Timeout is expected when no messages are available
                    pass
                except Exception as e:
                    log(f"Unexpected error in consumer loop: {str(e)}", level="error")
                    time.sleep(1)  # Brief pause before retry
                    
        except KeyboardInterrupt:
            log("Consumer interrupted by user")
        except Exception as e:
            log(f"Fatal error in consumer: {str(e)}", level="error")
        finally:
            self._running = False
            if self._client:
                self._client.close()
                log("Redis connection closed")
            log("ScanningQueueConsumer stopped")
    
    def stop_consuming(self):
        """Stop the consumer gracefully"""
        log("Stopping ScanningQueueConsumer...")
        self._running = False
    
    def health_check(self) -> bool:
        """Check if the consumer can connect to Redis"""
        try:
            client = self._get_redis_client()
            if client is None:
                return False
            
            client.ping()
            return True
        except Exception as e:
            log(f"Health check failed: {str(e)}", level="error")
            return False 