from django.http import JsonResponse
import re
from ..utils.jwt_utils import verify_token, decode_token
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
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that don't require authentication
        self.public_paths = [
            r'^/login/?$',
            r'^/register/?$',
        ]
    
    def is_public_path(self, path):
        """Check if the path is public (doesn't require authentication)"""
        for pattern in self.public_paths:
            if re.match(pattern, path):
                return True
        return False
    
    def __call__(self, request):
        # Check if we're in async mode
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        
        # Log the request path to help with debugging
        logger.info(f"JWT Middleware processing request | Path: {request.path}")
        
        # Synchronous flow
        if self.is_public_path(request.path):
            logger.info(f"Public path detected, skipping authentication | Path: {request.path}")
            return self.get_response(request)
            
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            logger.info(f"Missing Authorization header | Path: {request.path}")
            return JsonResponse({
                'error': 'Missing Authorization header'
            }, status=401)
            
        if not auth_header.startswith('Bearer '):
            logger.info(f"Invalid Authorization format | Header: {auth_header[:15]}... | Path: {request.path}")
            return JsonResponse({
                'error': 'Authorization header must start with Bearer'
            }, status=401)
            
        token = auth_header.split(' ')[1]
        logger.info(f"Token received | Token prefix: {token[:15]}... | Path: {request.path}")
        
        # Verify token
        try:
            # Attempt to decode token manually to get better error information
            payload = jwt.decode(token, "ABCD1234", algorithms=['HS256'])
            logger.info(f"Token validated successfully | Path: {request.path}")
            # Add user data to request
            request.user_data = payload
            return self.get_response(request)
        except jwt.ExpiredSignatureError:
            logger.info(f"Token expired | Path: {request.path}")
            return JsonResponse({
                'error': 'Token has expired'
            }, status=401)
        except jwt.InvalidTokenError as e:
            logger.info(f"Invalid token: {str(e)} | Path: {request.path}")
            return JsonResponse({
                'error': f'Invalid token: {str(e)}'
            }, status=401)
    
    async def __acall__(self, request):
        # Log the request path for async requests
        logger.info(f"JWT Middleware processing async request | Path: {request.path}")
        
        # Asynchronous flow
        if self.is_public_path(request.path):
            logger.info(f"Public path detected (async), skipping authentication | Path: {request.path}")
            return await self.get_response(request)
            
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            logger.info(f"Missing Authorization header (async) | Path: {request.path}")
            return JsonResponse({
                'error': 'Missing Authorization header'
            }, status=401)
            
        if not auth_header.startswith('Bearer '):
            logger.info(f"Invalid Authorization format (async) | Header: {auth_header[:15]}... | Path: {request.path}")
            return JsonResponse({
                'error': 'Authorization header must start with Bearer'
            }, status=401)
            
        token = auth_header.split(' ')[1]
        logger.info(f"Token received (async) | Token prefix: {token[:15]}... | Path: {request.path}")
        
        # Verify token
        try:
            # Attempt to decode token manually to get better error information
            payload = jwt.decode(token, "ABCD1234", algorithms=['HS256'])
            logger.info(f"Token validated successfully (async) | Path: {request.path}")
            # Add user data to request
            request.user_data = payload
            return await self.get_response(request)
        except jwt.ExpiredSignatureError:
            logger.info(f"Token expired (async) | Path: {request.path}")
            return JsonResponse({
                'error': 'Token has expired'
            }, status=401)
        except jwt.InvalidTokenError as e:
            logger.info(f"Invalid token (async): {str(e)} | Path: {request.path}")
            return JsonResponse({
                'error': f'Invalid token: {str(e)}'
            }, status=401) 