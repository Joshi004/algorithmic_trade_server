import jwt
import datetime
from typing import Dict, Any, Optional

# Hard-coded secret keys
LLT_SECRET_KEY = "ABCD1234"  # LLT (Long Lived Token) secret key
SLT_SECRET_KEY = "9876ZYXW"  # SLT (Short Lived Token) secret key

# Expiration times - Declared constants
LLT_EXPIRY_HOURS = 24  # 24 hours for LLT
SLT_EXPIRY_MINUTES = 15  # 1 minute for SLT

def generate_token(payload: Dict[str, Any]) -> str:
    """
    Generate an LLT from the given payload.
    Legacy method maintained for backwards compatibility.
    
    Args:
        payload: Dictionary containing data to be encoded in the token
        
    Returns:
        JWT token string
    """
    return generate_llt(payload)

def generate_llt(payload: Dict[str, Any]) -> str:
    """
    Generate an LLT (Long Lived Token) from the given payload.
    
    Args:
        payload: Dictionary containing data to be encoded in the token
        
    Returns:
        JWT token string
    """
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=LLT_EXPIRY_HOURS)
    token_payload = {
        **payload,
        'exp': expiration,
        'token_type': 'llt'
    }
    
    token = jwt.encode(token_payload, LLT_SECRET_KEY, algorithm='HS256')
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token

def generate_slt(payload: Dict[str, Any]) -> str:
    """
    Generate an SLT (Short Lived Token) from the given payload.
    
    Args:
        payload: Dictionary containing data to be encoded in the token
        
    Returns:
        JWT token string
    """
    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=SLT_EXPIRY_MINUTES)
    token_payload = {
        **payload,
        'exp': expiration,
        'token_type': 'slt'
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
    payload = decode_llt(token)
    if payload:
        return payload
    
    return decode_slt(token)

def decode_llt(token: str) -> Optional[Dict[str, Any]]:
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
        if 'token_type' not in payload or payload.get('token_type') == 'llt':
            return payload
        return None
    except jwt.PyJWTError:
        return None

def decode_slt(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a short-lived JWT token and return the payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing the decoded payload or None if token is invalid
    """
    try:
        payload = jwt.decode(token, SLT_SECRET_KEY, algorithms=['HS256'])
        if payload.get('token_type') == 'slt':
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

def verify_llt(token: str) -> bool:
    """
    Verify if a long-lived token is valid.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is valid, False otherwise
    """
    return decode_llt(token) is not None

def verify_slt(token: str) -> bool:
    """
    Verify if a short-lived token is valid.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is valid, False otherwise
    """
    return decode_slt(token) is not None
