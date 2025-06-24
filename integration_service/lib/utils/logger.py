"""
Standardized logging for Integration Service

This module provides standardized logging using the centralized ATS logging utilities.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from ats_base.logging_utils import create_service_logger

# Create standardized logger for integration service
logger = create_service_logger('integration_service', 'integration_utils')

def log(message: str, level: str = "info") -> None:
    """
    Legacy logging function - migrated to use standardized logging.
    
    Args:
        message: The message to log
        level: Log level (debug, info, warning, error, critical)
    """
    # Map legacy levels to new logger methods
    level_mapping = {
        'debug': logger.debug,
        'info': logger.info, 
        'warning': logger.warning,
        'error': logger.error,
        'critical': logger.critical
    }
    
    log_func = level_mapping.get(level.lower(), logger.info)
    log_func(message) 