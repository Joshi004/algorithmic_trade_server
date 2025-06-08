import json
import time
import redis
import os
from datetime import datetime
from typing import Dict, Any, Optional

from django.conf import settings
from scanning_service.lib.utils.logger import log
from scanning_service.lib.utils.redis import restore_from_redis_stream, create_consumer_client
from scanning_service.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from scanning_service.lib.data_providers import IntegrationServiceProvider, TMUServiceProvider


class ScanningQueueConsumer:
    """
    Consumer for processing trade session scanning events from Redis stream.
    Reads from 'scanning_queue' stream and processes trade session events.
    """
    
    def __init__(self):
        """Initialize the consumer with Redis connection and configuration"""
        # Stream and consumer configuration
        self.stream_name = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        self.consumer_group = "scanning_service_group"
        self.consumer_name = f"scanning_consumer_{int(time.time())}"
        
        # Create Redis consumer client using new structure
        self.redis_consumer = create_consumer_client(self.consumer_group, self.consumer_name)
        
        self._running = False
        self._scanner_factory = ScannerAlgoFactory()
        
        log(f"Initialized ScanningQueueConsumer with consumer name: {self.consumer_name}")
    

    
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
            scanning_algo_id = algo_config.get('scanning_algorithm_id', 1)  # Default to UDTS (ID 1)
            tracking_algo_id = algo_config.get('tracking_algorithm_id', 1)  # Default to tracking algo ID 1
            
            log(f"Starting scanner for trade session {trade_session_id}:")
            log(f"  - User ID: {user_id}")
            log(f"  - Trading Frequency: {trading_frequency}")
            log(f"  - Scanning Algorithm ID: {scanning_algo_id}")
            log(f"  - Tracking Algorithm ID: {tracking_algo_id}")
            log(f"  - Is Dummy: {is_dummy}")
            
            # Create data providers
            integration_provider = IntegrationServiceProvider(user_id)
            tmu_provider = TMUServiceProvider(user_id)
            
            # Get scanner instance using factory (factory handles singleton behavior)
            scanner = self._scanner_factory.get_scanner(scanning_algo_id, trading_frequency)
            
            if scanner is None:
                log(f"Unknown scanning algorithm ID: {scanning_algo_id}", level="error")
                return False
            
            # Configure the scanner with required parameters
            # Note: user_id and trade_session_id are passed but not stored as instance state
            scanner.configure(
                trade_freq=trading_frequency,
                user_id=user_id,
                trade_session_id=trade_session_id,
                integration_provider=integration_provider,
                tmu_provider=tmu_provider
            )
            
            # Start scanning in a separate thread
            # Pass trade_session_id as parameter since it's not stored in scanner
            scanner.fetch_instrument_tokens_and_start_tracking(user_id, trade_session_id, is_dummy)
            
            log(f"Successfully started scanner for trade session {trade_session_id}")
            return True
            
        except Exception as e:
            log(f"Error starting scanner: {str(e)}", level="error")
            return False
    
    def _handle_trade_session_terminated(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle trade session terminated event.
        
        Note: Since we no longer cache scanner instances, we cannot directly stop
        specific scanners. The singleton scanners will continue running for their
        frequency until stopped by container shutdown or other mechanisms.
        
        Args:
            event_data: The event data containing trade session details
            
        Returns:
            bool: True (always successful as no action needed)
        """
        try:
            trade_session_id = event_data.get('trade_session_id')
            user_id = event_data.get('user_id')
            
            log(f"Trade session terminated: {trade_session_id} for user: {user_id}")
            log("Note: Scanner instances are frequency-based singletons and continue running")
            
            return True
            
        except Exception as e:
            log(f"Error handling session termination: {str(e)}", level="error")
            return False
    
    def start_consuming(self):
        """Start consuming messages from the scanning queue"""
        try:
            log("Starting ScanningQueueConsumer...")
            
            # Test Redis connection using new consumer client
            if not self.redis_consumer.health_check():
                log("Failed to connect to Redis, cannot start consumer", level="error")
                return
            
            log("Redis connection established successfully")
            
            # Ensure consumer group exists using new consumer client
            if not self.redis_consumer.ensure_consumer_group(self.stream_name):
                log("Failed to ensure consumer group, cannot start consumer", level="error")
                return
            
            self._running = True
            log(f"Consumer started successfully, listening on stream '{self.stream_name}'")
            
            while self._running:
                try:
                    # Read messages from the stream using new consumer client
                    messages = self.redis_consumer.read_from_stream(self.stream_name)
                    
                    if messages:
                        for stream, stream_messages in messages:
                            for message_id, fields in stream_messages:
                                try:
                                    # Unflatten the event data
                                    event_data = restore_from_redis_stream(fields)
                                    
                                    # Process the event
                                    success = self._process_event(event_data)
                                    
                                    if success:
                                        # Acknowledge the message using new consumer client
                                        if self.redis_consumer.acknowledge_message(self.stream_name, message_id):
                                            log(f"Acknowledged message {message_id}")
                                        else:
                                            log(f"Failed to acknowledge message {message_id}", level="error")
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
            self.redis_consumer.close()
            log("ScanningQueueConsumer stopped")
    
    def stop_consuming(self):
        """Stop the consumer gracefully"""
        log("Stopping ScanningQueueConsumer...")
        self._running = False
        log("ScanningQueueConsumer stopped")
    
    def health_check(self) -> bool:
        """Check if the consumer can connect to Redis"""
        return self.redis_consumer.health_check() 