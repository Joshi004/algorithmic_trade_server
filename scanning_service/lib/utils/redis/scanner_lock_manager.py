import redis
import time
import uuid
from typing import Optional, Tuple
from django.conf import settings
from scanning_service.lib.utils.logger import log


class ScannerLockManager:
    """
    Manages distributed locks for scanner instances using Redis.
    Ensures only one container processes a specific algorithm+frequency combination.
    """
    
    def __init__(self, redis_client: redis.Redis = None):
        """
        Initialize the lock manager with a Redis client.
        
        Args:
            redis_client: Optional Redis client instance. If not provided, creates a new one.
        """
        if redis_client is None:
            redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
            redis_port = getattr(settings, 'REDIS_PORT', 6379)
            redis_db = getattr(settings, 'REDIS_DB', 0)
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
        else:
            self.redis_client = redis_client
        
        # Generate unique container ID
        self.container_id = f"container_{uuid.uuid4().hex[:8]}"
        log(f"ScannerLockManager initialized with container ID: {self.container_id}")
    
    def _get_lock_key(self, algorithm_id: int, frequency: str) -> str:
        """
        Generate the Redis key for a scanner lock.
        
        Args:
            algorithm_id: The scanning algorithm ID
            frequency: The trading frequency
            
        Returns:
            str: The Redis key for the lock
        """
        return f"scanner_lock:{algorithm_id}:{frequency}"
    
    def acquire_lock(self, algorithm_id: int, frequency: str, ttl_seconds: int = 300) -> bool:
        """
        Attempt to acquire a lock for a scanner instance.
        
        Args:
            algorithm_id: The scanning algorithm ID
            frequency: The trading frequency
            ttl_seconds: Time to live for the lock in seconds (default: 300 = 5 minutes)
            
        Returns:
            bool: True if lock acquired, False otherwise
        """
        lock_key = self._get_lock_key(algorithm_id, frequency)
        
        try:
            # Try to set the lock with NX (only if not exists) and EX (expiry)
            result = self.redis_client.set(
                lock_key,
                self.container_id,
                nx=True,  # Only set if key doesn't exist
                ex=ttl_seconds  # Set expiry
            )
            
            if result:
                log(f"Successfully acquired lock for scanner {algorithm_id}:{frequency}")
                return True
            else:
                # Lock already exists, check if it's owned by us
                current_owner = self.redis_client.get(lock_key)
                if current_owner == self.container_id:
                    log(f"Lock already owned by this container for scanner {algorithm_id}:{frequency}")
                    # Renew the lock
                    self.renew_lock(algorithm_id, frequency, ttl_seconds)
                    return True
                else:
                    log(f"Lock already held by container {current_owner} for scanner {algorithm_id}:{frequency}")
                    return False
                    
        except Exception as e:
            log(f"Error acquiring lock for scanner {algorithm_id}:{frequency}: {str(e)}", level="error")
            return False
    
    def renew_lock(self, algorithm_id: int, frequency: str, ttl_seconds: int = 300) -> bool:
        """
        Renew an existing lock if owned by this container.
        
        Args:
            algorithm_id: The scanning algorithm ID
            frequency: The trading frequency
            ttl_seconds: New time to live for the lock in seconds
            
        Returns:
            bool: True if lock renewed, False otherwise
        """
        lock_key = self._get_lock_key(algorithm_id, frequency)
        
        try:
            # Use Lua script to atomically check ownership and renew
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            
            result = self.redis_client.eval(
                lua_script,
                1,  # Number of keys
                lock_key,  # KEYS[1]
                self.container_id,  # ARGV[1]
                ttl_seconds  # ARGV[2]
            )
            
            if result:
                log(f"Successfully renewed lock for scanner {algorithm_id}:{frequency}")
                return True
            else:
                log(f"Failed to renew lock for scanner {algorithm_id}:{frequency} - not owned by this container", level="warning")
                return False
                
        except Exception as e:
            log(f"Error renewing lock for scanner {algorithm_id}:{frequency}: {str(e)}", level="error")
            return False
    
    def release_lock(self, algorithm_id: int, frequency: str) -> bool:
        """
        Release a lock if owned by this container.
        
        Args:
            algorithm_id: The scanning algorithm ID
            frequency: The trading frequency
            
        Returns:
            bool: True if lock released, False otherwise
        """
        lock_key = self._get_lock_key(algorithm_id, frequency)
        
        try:
            # Use Lua script to atomically check ownership and delete
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = self.redis_client.eval(
                lua_script,
                1,  # Number of keys
                lock_key,  # KEYS[1]
                self.container_id  # ARGV[1]
            )
            
            if result:
                log(f"Successfully released lock for scanner {algorithm_id}:{frequency}")
                return True
            else:
                log(f"Failed to release lock for scanner {algorithm_id}:{frequency} - not owned by this container", level="warning")
                return False
                
        except Exception as e:
            log(f"Error releasing lock for scanner {algorithm_id}:{frequency}: {str(e)}", level="error")
            return False
    
    def check_lock(self, algorithm_id: int, frequency: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a lock exists and who owns it.
        
        Args:
            algorithm_id: The scanning algorithm ID
            frequency: The trading frequency
            
        Returns:
            Tuple[bool, Optional[str]]: (lock_exists, owner_container_id)
        """
        lock_key = self._get_lock_key(algorithm_id, frequency)
        
        try:
            owner = self.redis_client.get(lock_key)
            if owner:
                return True, owner
            else:
                return False, None
                
        except Exception as e:
            log(f"Error checking lock for scanner {algorithm_id}:{frequency}: {str(e)}", level="error")
            return False, None
    
    def is_lock_owned_by_us(self, algorithm_id: int, frequency: str) -> bool:
        """
        Check if a lock is owned by this container.
        
        Args:
            algorithm_id: The scanning algorithm ID
            frequency: The trading frequency
            
        Returns:
            bool: True if lock is owned by this container, False otherwise
        """
        exists, owner = self.check_lock(algorithm_id, frequency)
        return exists and owner == self.container_id 