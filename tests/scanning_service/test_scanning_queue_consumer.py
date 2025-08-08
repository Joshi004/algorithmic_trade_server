"""
Integration Tests for ScanningQueueConsumer

These tests verify the scanning queue consumer initialization and functionality
using real Redis integration and database connections. Tests cover consumer
initialization, signal handling, and Redis connection validation.
"""

import pytest
import signal
import time
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

from scanning_service.consumers.scanning_queue_consumer import ScanningQueueConsumer
from django.conf import settings


@pytest.mark.integration
@pytest.mark.requires_db 
@pytest.mark.redis
class TestScanningQueueConsumerInitialization:
    """
    Integration Tests for ScanningQueueConsumer Initialization
    
    These tests verify the consumer initialization process including Redis client creation,
    lock manager initialization, signal handler setup, and initial state configuration.
    Tests use real Redis integration without mocking.
    """
    
    def test_successful_consumer_initialization(self, redis_data_manager):
        """
        Test Case A1.1: Successful Consumer Initialization
        
        Setup: Valid Redis configuration, accessible Redis server
        Action: Create ScanningQueueConsumer instance
        Verification:
            * Consumer name contains timestamp
            * Redis consumer client created successfully
            * Lock manager initialized
            * Signal handlers registered (SIGTERM, SIGINT)
            * _running flag set to False initially
        """
        # Clear any existing Redis state before test
        scanning_queue = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        redis_data_manager.clear_stream_completely(scanning_queue)
        
        # Store original signal handlers to restore later
        original_sigterm_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        try:
            # Record the time before creating consumer to verify timestamp in name
            time_before_creation = int(time.time())
            
            # Action: Create ScanningQueueConsumer instance
            consumer = ScanningQueueConsumer()
            
            # Record the time after creation
            time_after_creation = int(time.time())
            
            # Verification 1: Consumer name contains timestamp
            assert hasattr(consumer, 'consumer_name'), "Consumer should have consumer_name attribute"
            assert consumer.consumer_name.startswith('scanning_consumer_'), "Consumer name should start with 'scanning_consumer_'"
            
            # Extract timestamp from consumer name
            timestamp_part = consumer.consumer_name.replace('scanning_consumer_', '')
            consumer_timestamp = int(timestamp_part)
            
            # Verify timestamp is within expected range (allowing for processing time)
            assert time_before_creation <= consumer_timestamp <= time_after_creation, \
                f"Consumer timestamp {consumer_timestamp} should be between {time_before_creation} and {time_after_creation}"
            
            # Verification 2: Redis consumer client created successfully
            assert hasattr(consumer, 'redis_consumer'), "Consumer should have redis_consumer attribute"
            assert consumer.redis_consumer is not None, "Redis consumer client should be initialized"
            
            # Verify Redis client can perform basic operations
            assert consumer.redis_consumer.health_check() == True, "Redis consumer client should pass health check"
            
            # Verify stream name configuration
            expected_stream_name = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
            assert consumer.stream_name == expected_stream_name, f"Stream name should be {expected_stream_name}"
            
            # Verify consumer group configuration
            assert consumer.consumer_group == "scanning_service_group", "Consumer group should be 'scanning_service_group'"

            # Verify redis_consumer reflects the same group and generated name
            assert hasattr(consumer.redis_consumer, 'consumer_group'), "redis_consumer should expose consumer_group"
            assert hasattr(consumer.redis_consumer, 'consumer_name'), "redis_consumer should expose consumer_name"
            assert consumer.redis_consumer.consumer_group == consumer.consumer_group, "redis_consumer group should match consumer group"
            assert consumer.redis_consumer.consumer_name == consumer.consumer_name, "redis_consumer name should match generated consumer name"
            
            # Verification 3: Lock manager initialized
            assert hasattr(consumer, 'lock_manager'), "Consumer should have lock_manager attribute"
            assert consumer.lock_manager is not None, "Lock manager should be initialized"
            
            # Verify lock manager is properly configured
            from scanning_service.lib.utils.redis.scanner_lock_manager import ScannerLockManager
            assert isinstance(consumer.lock_manager, ScannerLockManager), "Lock manager should be ScannerLockManager instance"
            
            # Verification 4: Signal handlers registered (SIGTERM, SIGINT)
            # Check that signal handlers have been modified from default
            current_sigterm_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
            current_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
            
            # Restore handlers and check they were different from default
            signal.signal(signal.SIGTERM, current_sigterm_handler)
            signal.signal(signal.SIGINT, current_sigint_handler)
            
            assert current_sigterm_handler != signal.SIG_DFL, "SIGTERM handler should be customized"
            assert current_sigint_handler != signal.SIG_DFL, "SIGINT handler should be customized"
            
            # Verification 5: _running flag set to False initially
            assert hasattr(consumer, '_running'), "Consumer should have _running attribute"
            assert consumer._running == False, "Initial _running flag should be False"
            
            # Additional verification: Scanner factory initialized
            assert hasattr(consumer, '_scanner_factory'), "Consumer should have _scanner_factory attribute"
            assert consumer._scanner_factory is not None, "Scanner factory should be initialized"
            
            # Verify scanner factory type
            from scanning_service.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
            assert isinstance(consumer._scanner_factory, ScannerAlgoFactory), "Scanner factory should be ScannerAlgoFactory instance"
            
            # Verify consumer can be stopped gracefully
            consumer.stop_consuming()
            assert consumer._running == False, "_running should remain False after stop_consuming()"
            
        finally:
            # Cleanup: Restore original signal handlers
            signal.signal(signal.SIGTERM, original_sigterm_handler)
            signal.signal(signal.SIGINT, original_sigint_handler)
            
            # Cleanup Redis connections if consumer was created
            if 'consumer' in locals():
                try:
                    if hasattr(consumer, 'redis_consumer') and consumer.redis_consumer:
                        consumer.redis_consumer.close()
                except Exception as e:
                    # Ignore cleanup errors to avoid masking test failures
                    pass
                
                try:
                    if hasattr(consumer, 'lock_manager') and consumer.lock_manager:
                        if hasattr(consumer.lock_manager, 'redis_client') and consumer.lock_manager.redis_client:
                            consumer.lock_manager.redis_client.close()
                except Exception as e:
                    # Ignore cleanup errors to avoid masking test failures  
                    pass
            
            # Clear Redis state after test
            redis_data_manager.clear_stream_completely(scanning_queue) 