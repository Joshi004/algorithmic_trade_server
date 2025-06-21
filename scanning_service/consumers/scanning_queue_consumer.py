import json
import time
import redis
import os
from datetime import datetime
from typing import Dict, Any, Optional

from django.conf import settings
# Removed transaction import - no longer using database transactions for scanner instances
from scanning_service.lib.utils.logger import log
from scanning_service.lib.utils.redis import restore_from_redis_stream, create_consumer_client
from scanning_service.lib.utils.redis.scanner_lock_manager import ScannerLockManager
from scanning_service.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from scanning_service.lib.data_providers import IntegrationServiceProvider, TMUServiceProvider
from integration_service.lib.common.system_user_utils import get_system_user_id
# Removed ScannerInstance import - no longer using scanner instances table
from trade_management_unit.models import ScanningAlgorithm, TradeSession


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
        
        # Initialize lock manager
        self.lock_manager = ScannerLockManager()
        
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
            log(f"Processing event with event data : {event_data}")
            event_id = event_data.get('event_id', 'unknown')
            event_type = event_data.get('event_type', 'unknown')
            trade_session_id = event_data.get('trade_session_id', 'unknown')
            
            log(f"Processing event {event_id}: {event_type} for trade session {trade_session_id}")
            
            # Handle different event types
            if event_type == 'trade_session_initiated':
                return self._handle_trade_session_initiated(event_data)
            elif event_type == 'trade_session_terminated':
                return self._handle_trade_session_terminated(event_data)
            elif event_type == 'resume_scanner':
                return self._handle_resume_scanner(event_data)
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
            event_data: The flat event data containing trade session details
            
        Returns:
            bool: True if scanner started successfully, False otherwise
        """
        return self._handle_scanner_event(event_data, is_resume=False)
    
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
    

    def _handle_resume_scanner(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle resume scanner event by validating active trade sessions and starting scanner if needed.
        
        Args:
            event_data: The event data containing trade session details (same structure as trade_session_initiated)
            
        Returns:
            bool: True if scanner resumed successfully or no action needed, False otherwise
        """
        return self._handle_scanner_event(event_data, is_resume=True)
    
    def _handle_scanner_event(self, event_data: Dict[str, Any], is_resume: bool = False) -> bool:
        """
        Unified handler for both trade_session_initiated and resume_scanner events.
        Both events use the same structure and processing logic.
        
        Args:
            event_data: The flat event data containing trade session details
            is_resume: True if this is a resume operation, False for new session
            
        Returns:
            bool: True if scanner started successfully, False otherwise
        """
        try:
            # Extract necessary information from flat structure
            trade_session_id = event_data.get('trade_session_id')
            user_id = event_data.get('user_id')
            trading_frequency = event_data.get('trading_frequency')
            is_dummy = event_data.get('is_dummy', False)
            
            # Extract algorithm configuration from event data
            scanning_algo_name = event_data.get('scanning_algorithm_name', 'UDTS')  # Default to UDTS
            initiation_algo_name = event_data.get('initiation_algorithm_name', 'Udts_slto')  # Default to Udts_slto
            termination_algo_name = event_data.get('termination_algorithm_name', 'Udts_slto')  # Default to Udts_slto
            
            operation_type = "Resuming" if is_resume else "Starting"
            log(f"{operation_type} scanner for trade session {trade_session_id}:")
            log(f"  - User ID: {user_id}")
            log(f"  - Trading Frequency: {trading_frequency}")
            log(f"  - Scanning Algorithm Name: {scanning_algo_name}")
            log(f"  - Initiation Algorithm Name: {initiation_algo_name}")
            log(f"  - Termination Algorithm Name: {termination_algo_name}")
            log(f"  - Is Dummy: {is_dummy}")
            
            # Get the scanning algorithm from database
            try:
                scanning_algorithm = ScanningAlgorithm.objects.get(name=scanning_algo_name)
                algorithm_id = scanning_algorithm.id
            except ScanningAlgorithm.DoesNotExist:
                log(f"Scanning algorithm '{scanning_algo_name}' not found in database", level="error")
                return False
            
            # For resume operations, validate that there are active trade sessions
            if is_resume:
                active_sessions = TradeSession.objects.filter(
                    scanning_algorithm_id=algorithm_id,
                    trading_frequency=trading_frequency,
                    status__in=['started'],  # Consider only started as active
                    is_active=True
                )
                
                if not active_sessions.exists():
                    log(f"No active trade sessions found for {scanning_algo_name}:{trading_frequency}. Cannot resume scanner.")
                    return False
                
                log(f"Found {active_sessions.count()} active trade sessions for {scanning_algo_name}:{trading_frequency}")
                
                # Check if lock already exists
                lock_exists, current_owner = self.lock_manager.check_lock(algorithm_id, trading_frequency)
                
                if lock_exists:
                    log(f"Lock already exists for {scanning_algo_name}:{trading_frequency} (owner: {current_owner}). No action needed.")
                    return True
            
            # Try to acquire lock for this scanner
            lock_acquired = self.lock_manager.acquire_lock(algorithm_id, trading_frequency)
            
            if not lock_acquired:
                log(f"Could not acquire lock for scanner {scanning_algo_name}:{trading_frequency}. Another container is processing it.")
                return True  # Return True as this is expected behavior, not an error
            
            # Lock acquired, proceed with starting the scanner
            log(f"Acquired lock for scanner {scanning_algo_name}:{trading_frequency}, proceeding to start scanner")
            
            # For resume operations, use first active session if event data is incomplete
            if is_resume and (not user_id or not trade_session_id):
                first_session = active_sessions.first()
                if not user_id:
                    user_id = first_session.user_id.public_id
                if not trade_session_id:
                    trade_session_id = first_session.id
                    is_dummy = first_session.dummy
            
            # Now proceed with creating the scanner
            try:
                # Create data providers using system credentials
                # Scanning operations should use system credentials as they fetch market data
                # that can be shared across all users
                system_user_id = get_system_user_id()
                system_integration_provider = IntegrationServiceProvider(system_user_id)
                system_tmu_provider = TMUServiceProvider(system_user_id)
                
                # Get scanner instance using factory (factory handles singleton behavior)
                scanner = self._scanner_factory.get_scanner(scanning_algo_name, trading_frequency)
                
                if scanner is None:
                    log(f"Unknown scanning algorithm name: {scanning_algo_name}", level="error")
                    # Release lock since scanner creation failed
                    self.lock_manager.release_lock(algorithm_id, trading_frequency)
                    return False
                
                # Store lock manager reference in scanner for heartbeat updates
                scanner._lock_manager = self.lock_manager
                scanner._algorithm_id = algorithm_id
                scanner._frequency = trading_frequency
                
                # Configure the scanner with required parameters
                scanner.configure(
                    trade_freq=trading_frequency,
                    user_id=user_id,
                    trade_session_id=trade_session_id,
                    integration_provider=system_integration_provider,
                    tmu_provider=system_tmu_provider
                )
                
                # Start scanning in a separate thread
                scanner.fetch_instrument_tokens_and_start_tracking(user_id, trade_session_id, is_dummy)
                
                success_msg = f"Successfully {'resumed' if is_resume else 'started'} scanner for trade session {trade_session_id}"
                log(success_msg)
                return True
                
            except Exception as e:
                # Failed to start scanner, release lock
                self.lock_manager.release_lock(algorithm_id, trading_frequency)
                log(f"Error starting scanner: {str(e)}", level="error")
                return False
            
        except Exception as e:
            operation_type = "resume scanner" if is_resume else "trade session initiated"
            log(f"Error handling {operation_type}: {str(e)}", level="error")
            return False

    def start_consuming(self):
        """Start consuming messages from the scanning queue called from the start_scanning_service"""
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
                                    # Debug: Log the raw fields from Redis stream
                                    log(f"Raw Redis stream fields for message {message_id}: {fields}")
                                    
                                    # Use flat fields directly instead of unflattering
                                    event_data = fields
                                    
                                    # Debug: Log the event data being processed
                                    log(f"Processing flat event data for message {message_id}: {event_data}")
                                    
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
                    log(f"Redis connection Timed Out:", level="error")
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
        log("Stopping ScanningQueueConsumer...")
        self._running = False
        log("ScanningQueueConsumer stopped")
    
    def health_check(self) -> bool:
        return self.redis_consumer.health_check() 