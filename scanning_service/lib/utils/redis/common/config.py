"""
Redis Configuration Management for Scanning Service.
Provides centralized configuration for Redis clients with environment-based settings.
"""
import os
from django.conf import settings
from scanning_service.lib.utils.logger import log


class RedisConfig:
    """Centralized Redis configuration management"""
    
    def __init__(self):
        """Initialize Redis configuration from Django settings"""
        self.host = getattr(settings, 'REDIS_HOST', 'localhost')
        self.port = getattr(settings, 'REDIS_PORT', 6379)
        self.db = getattr(settings, 'REDIS_DB', 0)
        self.socket_timeout = getattr(settings, 'REDIS_SOCKET_TIMEOUT', 5)
        self.socket_connect_timeout = getattr(settings, 'REDIS_SOCKET_CONNECT_TIMEOUT', 5)
        self.health_check_interval = getattr(settings, 'REDIS_HEALTH_CHECK_INTERVAL', 30)
        
        # Stream names
        self.scanning_queue_stream = getattr(settings, 'REDIS_STREAM_SCANNING_QUEUE', 'scanning_queue')
        self.initiation_queue_stream = getattr(settings, 'REDIS_STREAM_INITIATION_QUEUE', 'initiation_queue')
        self.scanner_status_stream = getattr(settings, 'REDIS_STREAM_SCANNER_STATUS', 'scanner_status_stream')
        
        # Consumer configuration
        self.consumer_batch_size = getattr(settings, 'REDIS_CONSUMER_BATCH_SIZE', 10)
        self.consumer_timeout = getattr(settings, 'REDIS_CONSUMER_TIMEOUT', 1000)  # milliseconds
    
    def get_base_config(self):
        """Get base Redis connection configuration"""
        return {
            'host': self.host,
            'port': self.port,
            'db': self.db,
            'decode_responses': True,
            'socket_timeout': self.socket_timeout,
            'socket_connect_timeout': self.socket_connect_timeout,
            'socket_keepalive': True,
            'health_check_interval': self.health_check_interval
        }
    
    def get_publisher_config(self):
        """Get Redis configuration optimized for publishers (fast, non-blocking)"""
        config = self.get_base_config()
        config.update({
            'connection_pool_kwargs': {
                'max_connections': 10,  # Small pool for publishers
                'retry_on_timeout': True,
                'retry_on_error': [ConnectionError, TimeoutError]
            }
        })
        return config
    
    def get_consumer_config(self):
        """Get Redis configuration optimized for consumers (blocking operations)"""
        config = self.get_base_config()
        config.update({
            'connection_pool_kwargs': {
                'max_connections': 5,   # Dedicated pool for consumers
                'retry_on_timeout': True,
                'socket_keepalive': True,
                'socket_keepalive_options': {}
            }
        })
        return config
    



# Singleton instance for configuration
_redis_config = None

def get_redis_config():
    """Get or create singleton Redis configuration instance"""
    global _redis_config
    if _redis_config is None:
        _redis_config = RedisConfig()
    return _redis_config 