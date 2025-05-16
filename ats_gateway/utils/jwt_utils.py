import jwt
import datetime
from typing import Dict, Any, Optional

# Hard-coded secret key as requested
SECRET_KEY = "ABCD1234"

def generate_token(payload: Dict[str, Any]) -> str:
    """
    Generate a JWT token from the given payload.
    
    Args:
        payload: Dictionary containing data to be encoded in the token
        
    Returns:
        JWT token string
    """
    # Add expiration time (24 hours from now)
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    token_payload = {
        **payload,
        'exp': expiration
    }
    
    # Encode the token
    token = jwt.encode(token_payload, SECRET_KEY, algorithm='HS256')
    # Ensure we return a string, not bytes
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token and return the payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing the decoded payload or None if token is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.PyJWTError:
        return None

def verify_token(token: str) -> bool:
    """
    Verify if a token is valid.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is valid, False otherwise
    """
    return decode_token(token) is not None 