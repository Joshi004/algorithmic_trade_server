import json
import time
import redis
import os
from datetime import datetime
from typing import Dict, Any, Optional

from django.conf import settings
from scanning_service.lib.utils.logger import log
from scanning_service.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from scanning_service.lib.data_providers import IntegrationServiceProvider, TMUServiceProvider


class ScanningQueueConsumer:
    """
    Consumer for processing trade session scanning events from Redis stream.
    Reads from 'scanning_queue' stream and processes trade session events.
    """
    
    def __init__(self):
        """Initialize the consumer with Redis connection and configuration"""
        # Get configuration from Django settings
        self.redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
        self.redis_port = getattr(settings, 'REDIS_PORT', 6379)
        self.redis_db = getattr(settings, 'REDIS_DB', 0)
        self.socket_timeout = getattr(settings, 'REDIS_SOCKET_TIMEOUT', 5)
        self.socket_connect_timeout = getattr(settings, 'REDIS_SOCKET_CONNECT_TIMEOUT', 5)
        self.health_check_interval = getattr(settings, 'REDIS_HEALTH_CHECK_INTERVAL', 30)
        
        # Stream and consumer configuration
        self.stream_name = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        self.consumer_group = "scanning_service_group"
        self.consumer_name = f"scanning_consumer_{int(time.time())}"
        self.batch_size = getattr(settings, 'REDIS_CONSUMER_BATCH_SIZE', 10)
        self.timeout = getattr(settings, 'REDIS_CONSUMER_TIMEOUT', 1000)  # milliseconds
        
        self._client = None
        self._running = False
        self._scanner_factory = ScannerAlgoFactory()
        self._active_scanners = {}  # Track active scanner instances
        
        log(f"Initialized ScanningQueueConsumer with consumer name: {self.consumer_name}")
    
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with proper configuration"""
        try:
            if self._client is None:
                self._client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    db=self.redis_db,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    decode_responses=True,
                    health_check_interval=self.health_check_interval
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
            
            # Handle different event types
            if event_type == 'trade_session_initiated':
                return self._handle_trade_session_initiated(event_data)
            elif event_type == 'trade_session_terminated':
                return self._handle_trade_session_terminated(event_data)
            else:
                log(f"Skipping unknown event type: {event_type}", level="warning")
                return True
            
        except Exception as e:
            log(f"Error processing event: {str(e)}", level="error")
            return False
    
    def _handle_trade_session_initiated(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle trade session initiated event by creating and starting a scanner.
        
        Args:
            event_data: The event data containing trade session details
            
        Returns:
            bool: True if scanner started successfully, False otherwise
        """
        try:
            # Extract necessary information
            trade_session_id = event_data.get('trade_session_id')
            user_id = event_data.get('user_id')
            trading_frequency = event_data.get('trading_frequency')
            is_dummy = event_data.get('is_dummy', False)
            
            # Extract algorithm configuration
            algo_config = event_data.get('algorithm', {}) or event_data.get('algorithm_config', {})
            scanning_algo_name = algo_config.get('scanning', {}).get('name', 'udts')
            tracking_algo_name = algo_config.get('tracking', {}).get('name', 'udts_slto')
            
            log(f"Starting scanner for trade session {trade_session_id}:")
            log(f"  - User ID: {user_id}")
            log(f"  - Trading Frequency: {trading_frequency}")
            log(f"  - Scanning Algorithm: {scanning_algo_name}")
            log(f"  - Tracking Algorithm: {tracking_algo_name}")
            log(f"  - Is Dummy: {is_dummy}")
            
            # Check if scanner already exists for this session
            scanner_key = f"{trade_session_id}_{user_id}"
            if scanner_key in self._active_scanners:
                existing_scanner = self._active_scanners[scanner_key]
                if existing_scanner.is_running():
                    log(f"Scanner already running for trade session {trade_session_id}", level="warning")
                    return True
                else:
                    # Remove the stopped scanner
                    del self._active_scanners[scanner_key]
            
            # Create data providers
            integration_provider = IntegrationServiceProvider(user_id)
            tmu_provider = TMUServiceProvider(user_id)
            
            # Create scanner instance with trade_session_id
            scanner = self._scanner_factory.get_scanner(
                scanning_algo_name=scanning_algo_name,
                tracking_algo_name=tracking_algo_name,
                trade_freq=trading_frequency,
                user_id=user_id,
                integration_provider=integration_provider,
                tmu_provider=tmu_provider,
                trade_session_id=trade_session_id  # Pass trade session ID
            )
            
            if scanner is None:
                log(f"Unknown scanning algorithm: {scanning_algo_name}", level="error")
                return False
            
            # Store scanner reference
            self._active_scanners[scanner_key] = scanner
            
            # Start scanning in a separate thread
            scanner.fetch_instrument_tokens_and_start_tracking(user_id, is_dummy)
            
            log(f"Successfully started scanner for trade session {trade_session_id}")
            return True
            
        except Exception as e:
            log(f"Error starting scanner: {str(e)}", level="error")
            return False
    
    def _handle_trade_session_terminated(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle trade session terminated event by stopping the scanner.
        
        Args:
            event_data: The event data containing trade session details
            
        Returns:
            bool: True if scanner stopped successfully, False otherwise
        """
        try:
            trade_session_id = event_data.get('trade_session_id')
            user_id = event_data.get('user_id')
            
            scanner_key = f"{trade_session_id}_{user_id}"
            
            if scanner_key in self._active_scanners:
                scanner = self._active_scanners[scanner_key]
                
                # Stop the scanner gracefully
                scanner.stop_scanning()
                
                # Remove from active scanners
                del self._active_scanners[scanner_key]
                log(f"Stopped and removed scanner for trade session {trade_session_id}")
            else:
                log(f"No active scanner found for trade session {trade_session_id}", level="warning")
            
            return True
            
        except Exception as e:
            log(f"Error stopping scanner: {str(e)}", level="error")
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
        """Stop the consumer and all active scanners gracefully"""
        log("Stopping ScanningQueueConsumer...")
        self._running = False
        
        # Stop all active scanners
        for scanner_key, scanner in list(self._active_scanners.items()):
            try:
                log(f"Stopping scanner: {scanner_key}")
                scanner.stop_scanning()
            except Exception as e:
                log(f"Error stopping scanner {scanner_key}: {str(e)}", level="error")
            finally:
                # Remove the scanner regardless of stop result
                del self._active_scanners[scanner_key]
        
        log(f"All {len(self._active_scanners)} scanners stopped")
    
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