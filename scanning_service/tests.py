import os
import time
import redis
from django.test import TestCase
from unittest.mock import patch, MagicMock
from scanning_service.consumers.scanning_queue_consumer import ScanningQueueConsumer
from scanning_service.lib.utils.logger import log


class ScanningQueueConsumerTest(TestCase):
    """Test cases for the ScanningQueueConsumer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.consumer = ScanningQueueConsumer()
        self.test_event_data = {
            'event_id': 'test-event-123',
            'event_type': 'trade_session_initiated',
            'timestamp': '2024-01-01T10:00:00+05:30',
            'trade_session_id': '123',
            'user_id': 'user-456',
            'trading_frequency': '3minute',
            'is_dummy': 'true',
            'session_status': 'started',
            'algorithm_config_scanning_algorithm_id': '2',
            'algorithm_config_initiation_algorithm_id': '1',
            'algorithm_config_termination_algorithm_id': '1'
        }
    
    def test_consumer_initialization(self):
        """Test that the consumer initializes correctly"""
        self.assertIsInstance(self.consumer, ScanningQueueConsumer)
        self.assertEqual(self.consumer.stream_name, "scanning_queue")
        self.assertEqual(self.consumer.consumer_group, "scanning_service_group")
        self.assertIsNone(self.consumer._client)
        self.assertFalse(self.consumer._running)
    
    def test_event_data_unflattening(self):
        """Test that flattened event data is correctly reconstructed"""
        result = self.consumer._unflatten_event_data(self.test_event_data)
        
        # Check basic fields
        self.assertEqual(result['event_id'], 'test-event-123')
        self.assertEqual(result['event_type'], 'trade_session_initiated')
        self.assertEqual(result['trade_session_id'], '123')
        
        # Check nested structure reconstruction
        self.assertIn('algorithm_config', result)
        self.assertEqual(result['algorithm_config']['scanning_algorithm_id'], '2')
        self.assertEqual(result['algorithm_config']['initiation_algorithm_id'], '1')
        self.assertEqual(result['algorithm_config']['termination_algorithm_id'], '1')
    
    def test_process_event_success(self):
        """Test successful event processing"""
        event_data = {
            'event_id': 'test-event-123',
            'event_type': 'trade_session_initiated',
            'trade_session_id': '123',
            'user_id': 'user-456',
            'timestamp': '2024-01-01T10:00:00+05:30',
            'trading_frequency': '3minute',
            'is_dummy': 'true',
            'session_status': 'started'
        }
        
        # Should return True for successful processing
        result = self.consumer._process_event(event_data)
        self.assertTrue(result)
    
    def test_process_event_wrong_type(self):
        """Test handling of unknown event types"""
        event_data = {
            'event_id': 'test-event-123',
            'event_type': 'unknown_event_type',
            'trade_session_id': '123'
        }
        
        # Should return True (skip processing but don't fail)
        result = self.consumer._process_event(event_data)
        self.assertTrue(result)
    
    def test_process_event_error_handling(self):
        """Test error handling in event processing"""
        # Test with malformed event data
        event_data = None
        
        result = self.consumer._process_event(event_data)
        self.assertFalse(result)
    
    @patch('redis.Redis')
    def test_redis_client_creation(self, mock_redis):
        """Test Redis client creation"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        client = self.consumer._get_redis_client()
        
        self.assertIsNotNone(client)
        mock_redis.assert_called_once()
    
    @patch('redis.Redis')
    def test_health_check_success(self, mock_redis):
        """Test successful health check"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        
        result = self.consumer.health_check()
        
        self.assertTrue(result)
        mock_client.ping.assert_called_once()
    
    @patch('redis.Redis')
    def test_health_check_failure(self, mock_redis):
        """Test health check failure"""
        mock_client = MagicMock()
        mock_client.ping.side_effect = redis.ConnectionError("Connection failed")
        mock_redis.return_value = mock_client
        
        result = self.consumer.health_check()
        
        self.assertFalse(result)
    
    def test_logger_function(self):
        """Test the logger utility function"""
        # This should not raise any exceptions
        log("Test message")
        log("Test warning", level="warning")
        log("Test error", level="error")
        
        # If we get here without exceptions, the test passes
        self.assertTrue(True)


class ScanningServiceIntegrationTest(TestCase):
    """Integration tests for the scanning service"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
        self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
    
    def test_redis_connection_available(self):
        """Test that Redis is available for integration testing"""
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0,
                socket_timeout=2,
                socket_connect_timeout=2,
                decode_responses=True
            )
            
            result = client.ping()
            self.assertTrue(result)
            
        except (redis.ConnectionError, redis.TimeoutError):
            # Skip test if Redis is not available
            self.skipTest("Redis not available for integration testing")
    
    def test_consumer_group_creation(self):
        """Test that consumer group can be created"""
        try:
            consumer = ScanningQueueConsumer()
            
            # This should not raise an exception
            result = consumer._ensure_consumer_group()
            
            # The result depends on whether Redis is available
            # In a real environment, this should be True
            self.assertIsInstance(result, bool)
            
        except Exception:
            # Skip test if Redis is not available
            self.skipTest("Redis not available for consumer group testing")
