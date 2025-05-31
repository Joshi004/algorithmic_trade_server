import logging
from datetime import datetime


def log(message: str, level: str = "info") -> None:
    """
    Simple logging function for scanning service.
    
    Args:
        message (str): The message to log
        level (str): Log level - "info", "warning", "error", "debug"
    """
    # Get the logger for scanning service
    logger = logging.getLogger('scanning_service')
    
    # Set default level if not configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    # Map string levels to logging levels
    level_mapping = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    
    log_level = level_mapping.get(level.lower(), logging.INFO)
    
    # Create timestamped message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [SCANNING_SERVICE] {message}"
    
    # Log the message
    logger.log(log_level, formatted_message)
    
    # Also print to console for immediate visibility in Docker
    print(formatted_message) 