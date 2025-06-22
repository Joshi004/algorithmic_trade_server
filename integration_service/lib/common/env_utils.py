import os
from dotenv import load_dotenv
from integration_service.lib.utils.logger import log

def load_env_variables():
    """Load environment variables from .env file."""
    env_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
        log(f"Loaded environment variables from {env_file}", level="info")
    else:
        log("No .env file found, will use OS environment variables", level="warning")

def get_env_variable(key, default=None, required=False):
    """
    Get environment variable with optional default value.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: If True, raise exception if not found
    
    Returns:
        Environment variable value or default
    """
    value = os.environ.get(key, default)
    
    if required and value is None:
        log(f"Environment variable {key} not found", level="warning")
        raise EnvironmentError(f"Required environment variable '{key}' not found")
    
    return value 