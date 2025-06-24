"""
Error classifier for determining if errors are temporary and should be retried.
"""

import re
from typing import Union


def is_temporary_error(error: Union[str, int, Exception]) -> bool:
    """
    Determine if an error is temporary and should be retried.
    
    Args:
        error: Error message (string), HTTP status code (int), or Exception object
        
    Returns:
        bool: True if the error is temporary and should be retried, False otherwise
    """
    # Handle HTTP status codes
    if isinstance(error, int):
        return _is_temporary_http_status(error)
    
    # Handle Exception objects
    if isinstance(error, Exception):
        error_str = str(error)
        return _is_temporary_error_message(error_str)
    
    # Handle string error messages
    if isinstance(error, str):
        return _is_temporary_error_message(error)
    
    # Unknown error type - assume not temporary
    return False


def _is_temporary_http_status(status_code: int) -> bool:
    """
    Determine if an HTTP status code represents a temporary error.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        bool: True if temporary, False otherwise
    """
    # Temporary HTTP status codes (should be retried)
    temporary_status_codes = {
        # 5xx Server errors (usually temporary)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
        507,  # Insufficient Storage
        508,  # Loop Detected
        510,  # Not Extended
        511,  # Network Authentication Required
        
        # Some 4xx that might be temporary
        408,  # Request Timeout
        429,  # Too Many Requests (rate limiting)
    }
    
    return status_code in temporary_status_codes


def _is_temporary_error_message(error_message: str) -> bool:
    """
    Determine if an error message represents a temporary error.
    
    Args:
        error_message: Error message string
        
    Returns:
        bool: True if temporary, False otherwise
    """
    if not error_message:
        return False
    
    error_lower = error_message.lower()
    
    # Network-related temporary errors
    temporary_patterns = [
        # Connection errors
        r'connection.*refused',
        r'connection.*reset',
        r'connection.*timeout',
        r'connection.*aborted',
        r'connection.*failed',
        r'network.*unreachable',
        r'host.*unreachable',
        r'name.*resolution.*failed',
        r'temporary.*failure',
        
        # Timeout errors
        r'timeout',
        r'timed.*out',
        r'read.*timeout',
        r'socket.*timeout',
        
        # Service unavailable
        r'service.*unavailable',
        r'server.*unavailable',
        r'temporarily.*unavailable',
        
        # Rate limiting
        r'rate.*limit',
        r'too.*many.*requests',
        r'quota.*exceeded',
        
        # Broker-specific temporary errors
        r'kite.*not.*ready',
        r'market.*closed',
        r'session.*expired',
        r'token.*expired',
        r'invalid.*session',
        
        # Database temporary errors
        r'database.*lock',
        r'deadlock',
        r'connection.*pool.*exhausted',
        
        # Redis temporary errors
        r'redis.*connection.*error',
        r'redis.*timeout',
        
        # General temporary indicators
        r'try.*again',
        r'retry',
        r'temporary',
        r'transient',
    ]
    
    # Check if error message matches any temporary pattern
    for pattern in temporary_patterns:
        if re.search(pattern, error_lower):
            return True
    
    # Permanent error patterns (explicitly not temporary)
    permanent_patterns = [
        r'authentication.*failed',
        r'unauthorized',
        r'forbidden',
        r'not.*found',
        r'invalid.*symbol',
        r'invalid.*token',
        r'invalid.*instrument',
        r'malformed.*request',
        r'bad.*request',
        r'permission.*denied',
        r'access.*denied',
    ]
    
    # Check if error message matches any permanent pattern
    for pattern in permanent_patterns:
        if re.search(pattern, error_lower):
            return False
    
    # Default: assume non-temporary for unknown errors
    return False 