import jwt
import datetime
from typing import Dict, Any, Optional

# Hard-coded secret keys
LLT_SECRET_KEY = "ABCD1234"  # Long-lived token secret key
SLT_SECRET_KEY = "9876ZYXW"  # Short-lived token secret key

# Expiration times
LLT_EXPIRY = 24  # hours
SLT_EXPIRY = 5   # minutes

def generate_token(payload: Dict[str, Any]) -> str:
    """
    Generate a long-lived JWT token from the given payload.
    Legacy method maintained for backwards compatibility.
    
    Args:
        payload: Dictionary containing data to be encoded in the token
        
    Returns:
        JWT token string
    """
    return generate_long_lived_token(payload)

def generate_long_lived_token(payload: Dict[str, Any]) -> str:
    """
    Generate a long-lived JWT token (24 hours) from the given payload.
    
    Args:
        payload: Dictionary containing data to be encoded in the token
        
    Returns:
        JWT token string
    """
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=LLT_EXPIRY)
    token_payload = {
        **payload,
        'exp': expiration,
        'token_type': 'long_lived'
    }
    
    token = jwt.encode(token_payload, LLT_SECRET_KEY, algorithm='HS256')
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token

def generate_short_lived_token(payload: Dict[str, Any]) -> str:
    """
    Generate a short-lived JWT token (5 minutes) from the given payload.
    
    Args:
        payload: Dictionary containing data to be encoded in the token
        
    Returns:
        JWT token string
    """
    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=SLT_EXPIRY)
    token_payload = {
        **payload,
        'exp': expiration,
        'token_type': 'short_lived'
    }
    
    token = jwt.encode(token_payload, SLT_SECRET_KEY, algorithm='HS256')
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token and return the payload.
    Legacy method maintained for backwards compatibility.
    Tries both token types.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing the decoded payload or None if token is invalid
    """
    # Try both token types
    payload = decode_long_lived_token(token)
    if payload:
        return payload
    
    return decode_short_lived_token(token)

def decode_long_lived_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a long-lived JWT token and return the payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing the decoded payload or None if token is invalid
    """
    try:
        payload = jwt.decode(token, LLT_SECRET_KEY, algorithms=['HS256'])
        # For backwards compatibility, consider tokens without type as long-lived
        if 'token_type' not in payload or payload.get('token_type') == 'long_lived':
            return payload
        return None
    except jwt.PyJWTError:
        return None

def decode_short_lived_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a short-lived JWT token and return the payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing the decoded payload or None if token is invalid
    """
    try:
        payload = jwt.decode(token, SLT_SECRET_KEY, algorithms=['HS256'])
        if payload.get('token_type') == 'short_lived':
            return payload
        return None
    except jwt.PyJWTError:
        return None

def verify_token(token: str) -> bool:
    """
    Verify if a token is valid.
    Legacy method maintained for backwards compatibility.
    Tries both token types.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is valid, False otherwise
    """
    return decode_token(token) is not None

def verify_long_lived_token(token: str) -> bool:
    """
    Verify if a long-lived token is valid.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is valid, False otherwise
    """
    return decode_long_lived_token(token) is not None

def verify_short_lived_token(token: str) -> bool:
    """
    Verify if a short-lived token is valid.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is valid, False otherwise
    """
    return decode_short_lived_token(token) is not None
