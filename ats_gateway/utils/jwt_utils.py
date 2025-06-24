import jwt
import datetime
import os
from typing import Dict, Any, Optional

# JWT Secret Keys from Environment Variables
# These keys are used to sign and verify JWT tokens
# In production, set these as secure environment variables in docker-compose.yml
LLT_SECRET_KEY = os.environ.get(
    'JWT_LONG_LIVED_TOKEN_SECRET', 
    'ABCD1234'  # Development fallback - change in production!
)

SLT_SECRET_KEY = os.environ.get(
    'JWT_SHORT_LIVED_TOKEN_SECRET',
    '9876ZYXW'  # Development fallback - change in production!
)

# Dedicated WebSocket Secret Key for enhanced security isolation
WEBSOCKET_SECRET_KEY = os.environ.get(
    'JWT_WEBSOCKET_TOKEN_SECRET',
    'WS_SEC_2024_ATS'  # Development fallback - change in production!
)

# Expiration times - Declared constants
LLT_EXPIRY_HOURS = 24  # 24 hours for LLT
SLT_EXPIRY_MINUTES = 15  # 15 minutes for SLT
WEBSOCKET_TOKEN_EXPIRY_SECONDS = 30  # 30 seconds for WebSocket tokens (security enhancement)

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

def generate_websocket_token(payload: Dict[str, Any]) -> str:
    """
    Generate a WebSocket-specific token with 30-second expiration for enhanced security.
    
    This token is specifically designed for WebSocket authentication with:
    - Very short expiration (30 seconds) to minimize security risk
    - Dedicated secret key (separate from SLT/LLT keys) for security isolation
    - Special token type to differentiate from regular API tokens
    - Scope limitation to WebSocket connections only
    
    Args:
        payload: Dictionary containing data to be encoded in the token
        
    Returns:
        JWT token string with 30-second expiration and dedicated secret key
    """
    expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=WEBSOCKET_TOKEN_EXPIRY_SECONDS)
    token_payload = {
        **payload,
        'exp': expiration,
        'token_type': 'websocket',  # Special type for WebSocket tokens
        'scope': 'websocket_only'   # Limit scope to WebSocket connections only
    }
    
    # Use dedicated WebSocket secret key for enhanced security isolation
    token = jwt.encode(token_payload, WEBSOCKET_SECRET_KEY, algorithm='HS256')
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

def decode_websocket_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a WebSocket-specific JWT token and return the payload.
    
    This function specifically handles WebSocket tokens with:
    - 30-second expiration for enhanced security
    - Dedicated secret key (separate from SLT/LLT keys) for security isolation
    - Special token type validation
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing the decoded payload or None if token is invalid
    """
    try:
        # Use dedicated WebSocket secret key for enhanced security isolation
        payload = jwt.decode(token, WEBSOCKET_SECRET_KEY, algorithms=['HS256'])
        if payload.get('token_type') == 'websocket':
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

def verify_websocket_token(token: str) -> bool:
    """
    Verify if a WebSocket token is valid.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is valid, False otherwise
    """
    return decode_websocket_token(token) is not None
