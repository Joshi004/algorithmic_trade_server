import os
import logging
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_file = find_dotenv(raise_error_if_not_found=False)
if env_file:
    load_dotenv(env_file)
    logger.info(f"Loaded environment variables from {env_file}")
else:
    logger.warning("No .env file found, will use OS environment variables")


def get_env_variable(key, default=None):
    """
    Get an environment variable from .env file or OS environment
    
    Args:
        key (str): The name of the environment variable
        default: The default value to return if the variable is not found
        
    Returns:
        The value of the environment variable or the default value
    """
    value = os.environ.get(key, default)
    if value is None:
        logger.warning(f"Environment variable {key} not found")
    return value 