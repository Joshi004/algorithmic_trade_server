"""
Base Redis Client for Scanning Service.
Provides common functionality for both publisher and consumer Redis clients.
"""
import redis
from abc import ABC, abstractmethod
from typing import Optional
from scanning_service.lib.utils.logger import log
from .config import get_redis_config


class BaseRedisClient(ABC):
    """Base class for Redis clients with common functionality"""
    
    def __init__(self, client_type: str):
        """
        Initialize base Redis client
        
        Args:
            client_type: Type of client ('publisher' or 'consumer')
        """
        self.client_type = client_type
        self.config = get_redis_config()
        self._client = None
        self._is_connected = False
    
    @abstractmethod
    def _get_client_config(self) -> dict:
        """Get client-specific Redis configuration"""
        pass
    
    def _create_client(self) -> Optional[redis.Redis]:
        """Create Redis client with appropriate configuration"""
        try:
            client_config = self._get_client_config()
            
            # Extract connection pool kwargs if present
            connection_pool_kwargs = client_config.pop('connection_pool_kwargs', None)
            
            # Create Redis client
            # Create connection pool with the extracted kwargs
            pool_config = client_config.copy()
            pool_config.update(connection_pool_kwargs)
            pool = redis.ConnectionPool(**pool_config)
            client = redis.Redis(connection_pool=pool)

            
            # Test the connection
            client.ping()
            self._is_connected = True
            
            log(f"{self.client_type.title()} Redis client connected - {self.config.host}:{self.config.port}")
            return client
            
        except redis.ConnectionError as e:
            log(f"Failed to connect {self.client_type} Redis client: {str(e)}", level="error")
            self._is_connected = False
            raise
        except Exception as e:
            log(f"Failed to create {self.client_type} Redis client: {str(e)}", level="error")
            self._is_connected = False
            raise
    
    def get_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client instance"""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    

    
    def health_check(self) -> bool:
        """Perform health check on Redis connection"""
        try:
            client = self.get_client()
            if client is None:
                return False
            
            # Test with ping
            result = client.ping()
            log(f"{self.client_type.title()} Redis health check: {'OK' if result else 'FAILED'}")
            return result
            
        except Exception as e:
            log(f"{self.client_type.title()} Redis health check failed: {str(e)}", level="error")
            return False
    
    def close(self):
        """Close Redis connection"""
        if self._client:
            try:
                # Close connection pool properly
                if hasattr(self._client, 'connection_pool') and self._client.connection_pool:
                    self._client.connection_pool.disconnect()
                    log(f"{self.client_type.title()} Redis connection pool disconnected")
                
                # Close the client
                self._client.close()
                log(f"{self.client_type.title()} Redis client connection closed")
            except Exception as e:
                log(f"Error closing {self.client_type} Redis client: {str(e)}", level="error")
            finally:
                self._client = None
                self._is_connected = False
    
    def __del__(self):
        """Destructor to ensure connections are closed"""
        try:
            if self._client is not None:
                self.close()
        except Exception:
            # Ignore errors during destruction
            pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.close()
    

    

    
 