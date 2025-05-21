from django.http import JsonResponse
import re
from ..utils.jwt_utils import decode_long_lived_token, decode_short_lived_token
import asyncio
import logging
import jwt

# Get logger
logger = logging.getLogger(__name__)

class JWTAuthMiddleware:
    """
    Middleware to check JWT token in the Authorization header for protected endpoints.
    
    Public endpoints like login and register are excluded from authentication.
    Compatible with both synchronous and asynchronous request handling.
    Supports both long-lived and short-lived tokens.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that don't require authentication
        self.public_paths = [
            r'^/login/?$',
            r'^/register/?$',
        ]
        # Refresh token endpoint - only accessible with long-lived token
        self.refresh_path = r'^/refresh-token/?$'
    
    def is_public_path(self, path):
        """Check if the path is public (doesn't require authentication)"""
        for pattern in self.public_paths:
            if re.match(pattern, path):
                return True
        return False
    
    def extract_token(self, request):
        """Extract and validate token from the authorization header"""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            logger.info(f"Missing Authorization header | Path: {request.path}")
            return None, JsonResponse({
                'error': 'Missing Authorization header'
            }, status=401)
            
        if not auth_header.startswith('Bearer '):
            logger.info(f"Invalid Authorization format | Header: {auth_header[:15]}... | Path: {request.path}")
            return None, JsonResponse({
                'error': 'Authorization header must start with Bearer'
            }, status=401)
            
        token = auth_header.split(' ')[1]
        # Strip quotes if present
        token = token.strip('"')
        logger.info(f"Token received | Token prefix: {token[:15]}... | Path: {request.path}")
        return token, None
    
    def process_refresh_endpoint(self, token, request, is_async=False):
        """Process a request to the refresh token endpoint"""
        log_prefix = "(async) " if is_async else ""
        
        # Attempt to decode as a long-lived token
        payload = decode_long_lived_token(token)
        
        if payload:
            logger.info(f"Long-lived token validated for refresh endpoint {log_prefix}| Path: {request.path}")
            request.user_data = payload
            return True, None
            
        # If we couldn't decode as a long-lived token, check if it's a short-lived token
        short_lived_payload = decode_short_lived_token(token)
        if short_lived_payload:
            logger.info(f"Short-lived token used for refresh endpoint (not allowed) {log_prefix}| Path: {request.path}")
            return False, JsonResponse({
                'error': 'Short-lived tokens cannot be used for token refresh. Use your long-lived token instead.',
            }, status=401)
        
        # Token is neither valid long-lived nor short-lived
        logger.info(f"Invalid token for refresh endpoint {log_prefix}| Path: {request.path}")
        return False, JsonResponse({
            'error': 'Invalid or expired token',
            'redirect_to_login': True
        }, status=401)
    
    def process_api_endpoint(self, token, request, is_async=False):
        """Process a request to a regular API endpoint"""
        log_prefix = "(async) " if is_async else ""
        
        # Attempt to decode as a short-lived token
        payload = decode_short_lived_token(token)
        
        if payload:
            logger.info(f"Short-lived token validated successfully {log_prefix}| Path: {request.path}")
            request.user_data = payload
            return True, None
            
        # If we couldn't decode as a short-lived token, check if it's a long-lived token
        long_lived_payload = decode_long_lived_token(token)
        if long_lived_payload:
            logger.info(f"Long-lived token used for API access (not allowed) {log_prefix}| Path: {request.path}")
            return False, JsonResponse({
                'error': 'Long-lived tokens can only be used for token refresh. Please use a short-lived token instead.',
                'please_refresh': True
            }, status=401)
        
        # Token is neither valid short-lived nor long-lived
        logger.info(f"Invalid token for API endpoint {log_prefix}| Path: {request.path}")
        return False, JsonResponse({
            'error': 'Invalid or expired token',
            'redirect_to_login': True
        }, status=401)
    
    def __call__(self, request):
        """Synchronous request handler"""
        # Check if we're in async mode
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        
        # Log the request path to help with debugging
        logger.info(f"JWT Middleware processing request | Path: {request.path}")
        
        # Skip authentication for public paths
        if self.is_public_path(request.path):
            logger.info(f"Public path detected, skipping authentication | Path: {request.path}")
            return self.get_response(request)
        
        # Extract token from request
        token, error = self.extract_token(request)
        if error:
            return error
            
        # Check if this is the refresh-token endpoint
        is_refresh_endpoint = bool(re.match(self.refresh_path, request.path))
        
        try:
            # Process based on endpoint type
            if is_refresh_endpoint:
                success, error = self.process_refresh_endpoint(token, request)
            else:
                success, error = self.process_api_endpoint(token, request)
            
            if success:
                return self.get_response(request)
            return error
            
        except jwt.ExpiredSignatureError:
            logger.info(f"Token expired | Path: {request.path}")
            return JsonResponse({
                'error': 'Token has expired',
                'redirect_to_login': True
            }, status=401)
        except jwt.InvalidTokenError as e:
            logger.info(f"Invalid token: {str(e)} | Path: {request.path}")
            return JsonResponse({
                'error': f'Invalid token: {str(e)}',
                'redirect_to_login': True
            }, status=401)
    
    async def __acall__(self, request):
        """Asynchronous request handler"""
        # Log the request path for async requests
        logger.info(f"JWT Middleware processing async request | Path: {request.path}")
        
        # Skip authentication for public paths
        if self.is_public_path(request.path):
            logger.info(f"Public path detected (async), skipping authentication | Path: {request.path}")
            return await self.get_response(request)
        
        # Extract token from request
        token, error = self.extract_token(request)
        if error:
            return error
            
        # Check if this is the refresh-token endpoint
        is_refresh_endpoint = bool(re.match(self.refresh_path, request.path))
        
        try:
            # Process based on endpoint type
            if is_refresh_endpoint:
                success, error = self.process_refresh_endpoint(token, request, is_async=True)
            else:
                success, error = self.process_api_endpoint(token, request, is_async=True)
            
            if success:
                return await self.get_response(request)
            return error
            
        except jwt.ExpiredSignatureError:
            logger.info(f"Token expired (async) | Path: {request.path}")
            return JsonResponse({
                'error': 'Token has expired',
                'redirect_to_login': True
            }, status=401)
        except jwt.InvalidTokenError as e:
            logger.info(f"Invalid token (async): {str(e)} | Path: {request.path}")
            return JsonResponse({
                'error': f'Invalid token: {str(e)}',
                'redirect_to_login': True
            }, status=401)
