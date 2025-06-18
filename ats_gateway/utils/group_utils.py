import redis
from django.conf import settings
import logging

# Get logger
logger = logging.getLogger(__name__)

# Redis connection for subscription tracking
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

def get_group_name(algorithm_id, frequency):
    """
    Generate group name using convention: scanner_<algorithm>_<frequency>
    Example: scanner_2_5min
    """
    return f"scanner_{algorithm_id}_{frequency}"

def increment_group_subscription(group_name):
    """
    Increment subscriber count for a group in Redis
    Returns the new count
    """
    redis_key = f"subs:{group_name}"
    count = redis_client.incr(redis_key)
    
    # Set TTL to 1 hour (3600 seconds) to prevent orphaned keys
    # This ensures keys are automatically cleaned up if not refreshed
    redis_client.expire(redis_key, 3600)
    
    logger.info(f"Incremented subscription count for {group_name}: {count} (TTL: 1h)")
    return count

def decrement_group_subscription(group_name):
    """
    Decrement subscriber count for a group in Redis
    Returns the new count (minimum 0)
    """
    redis_key = f"subs:{group_name}"
    count = redis_client.decr(redis_key)
    # Ensure count doesn't go below 0
    if count < 0:
        redis_client.set(redis_key, 0)
        count = 0
    logger.info(f"Decremented subscription count for {group_name}: {count}")
    return count

def get_group_subscription_count(group_name):
    """
    Get current subscriber count for a group
    Returns 0 if key doesn't exist
    """
    redis_key = f"subs:{group_name}"
    count = redis_client.get(redis_key)
    return int(count) if count else 0

def cleanup_group_subscription(group_name):
    """
    Remove subscription tracking for a group if count is 0
    """
    redis_key = f"subs:{group_name}"
    count = get_group_subscription_count(group_name)
    if count <= 0:
        redis_client.delete(redis_key)
        logger.info(f"Cleaned up subscription tracking for {group_name}") 