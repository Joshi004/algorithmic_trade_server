from django.http import JsonResponse
import re
import asyncio
import jwt
from django.conf import settings
from ..utils.jwt_utils import decode_llt, decode_slt
from ats_gateway.utils.logger import log

class JWTAuthMiddleware():
    """
    Middleware to check JWT tokens in HTTP-only cookies for protected endpoints.
    
    Public endpoints like login and register are excluded from authentication.
    Compatible with both synchronous and asynchronous request handling.
    Supports both LLT and SLT:
    - LLT (from 'llt' cookie) are only accepted for token refresh
    - SLT (from 'slt' cookie) are used for regular API access
    - Internal service requests with 'X-Internal-Service-Token' header are allowed
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that don't require authentication
        self.public_paths = [
            r'^/login/?$',
            r'^/register/?$',
            r'^/logout/?$',
        ]
        # Refresh token endpoint - only accessible with LLT
        self.refresh_path = r'^/refresh-token/?$'
        # Internal service token from settings
        self.internal_service_token = getattr(settings, 'INTERNAL_SERVICE_TOKEN', 'internal-service-secret-token-change-in-production')
    
    def is_public_path(self, path):
        """Check if the path is public (doesn't require authentication)"""
        for pattern in self.public_paths:
            if re.match(pattern, path):
                return True
        return False
    
    def is_internal_service_request(self, request):
        """Check if the request is from an internal service"""
        internal_token = request.headers.get('X-Internal-Service-Token')
        if internal_token and internal_token == self.internal_service_token:
            log(f"Internal service request detected | Path: {request.path}", level="info")
            return True
        return False

    def extract_token(self, request):
        """Extract and validate token from HTTP-only cookies"""
        # Check if this is the refresh-token endpoint
        is_refresh_endpoint = bool(re.match(self.refresh_path, request.path))
        
        if is_refresh_endpoint:
            # For refresh endpoint, extract LLT from cookie
            token = request.COOKIES.get('llt')
            if not token:
                log(f"Missing llt cookie for refresh endpoint | Path: {request.path}", level="info")
                return None, JsonResponse({
                    'error': 'LLT cookie not found. Please login again.',
                    'redirect_to_login': True
                }, status=401)
        else:
            # For regular API endpoints, extract SLT from cookie
            token = request.COOKIES.get('slt')
            if not token:
                log(f"Missing slt cookie for API endpoint | Path: {request.path}", level="info")
                return None, JsonResponse({
                    'error': 'Authentication required. Please login.',
                    'redirect_to_login': True
                }, status=401)
        
        # Strip quotes if present (though cookies shouldn't have them)
        token = token.strip('"') if token else None
        # Log token extraction without exposing token value
        log(f"Token extracted from cookie | Path: {request.path}", level="info")
        return token, None
    
    def process_refresh_endpoint(self, token, request, is_async=False):
        """Process a request to the refresh token endpoint"""
        log_prefix = "(async) " if is_async else ""
        
        # Attempt to decode as an LLT
        payload = decode_llt(token)
        
        if payload:
            log(f"LLT validated for refresh endpoint {log_prefix}| Path: {request.path}", level="info")
            request.user_data = payload
            return True, None
            
        # If we couldn't decode as an LLT, check if it's an SLT
        slt_payload = decode_slt(token)
        if slt_payload:
            log(f"SLT used for refresh endpoint (not allowed) {log_prefix}| Path: {request.path}", level="info")
            return False, JsonResponse({
                'error': 'SLT cannot be used for token refresh. Use your LLT instead.',
            }, status=401)
        
        # Token is neither valid LLT nor SLT
        log(f"Invalid token for refresh endpoint {log_prefix}| Path: {request.path}", level="info")
        return False, JsonResponse({
            'error': 'Invalid or expired token',
            'redirect_to_login': True
        }, status=401)
    
    def process_api_endpoint(self, token, request, is_async=False):
        """Process a request to a regular API endpoint"""
        log_prefix = "(async) " if is_async else ""
        
        # Attempt to decode as an SLT
        payload = decode_slt(token)
        
        if payload:
            log(f"SLT validated successfully {log_prefix}| Path: {request.path}", level="info")
            request.user_data = payload
            return True, None
            
        # If we couldn't decode as an SLT, check if it's an LLT
        llt_payload = decode_llt(token)
        if llt_payload:
            log(f"LLT used for API access (not allowed) {log_prefix}| Path: {request.path}", level="info")
            return False, JsonResponse({
                'error': 'LLT can only be used for token refresh. Please use an SLT instead.',
                'please_refresh': True
            }, status=401)
        
        # Token is neither valid SLT nor LLT
        log(f"Invalid token for API endpoint {log_prefix}| Path: {request.path}", level="info")
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
        log(f"JWT Middleware processing request | Path: {request.path}", level="info")
        
        # Skip authentication for public paths
        if self.is_public_path(request.path):
            log(f"Public path detected, skipping authentication | Path: {request.path}", level="info")
            return self.get_response(request)
        
        # Check if this is an internal service request
        if self.is_internal_service_request(request):
            log(f"Internal service request, skipping JWT authentication | Path: {request.path}", level="info")
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
            log(f"Token expired | Path: {request.path}", level="info")
            return JsonResponse({
                'error': 'Token has expired',
                'redirect_to_login': True
            }, status=401)
        except jwt.InvalidTokenError as e:
            log(f"Invalid token: {str(e)} | Path: {request.path}", level="info")
            return JsonResponse({
                'error': f'Invalid token: {str(e)}',
                'redirect_to_login': True
            }, status=401)
    
    async def __acall__(self, request):
        """Asynchronous request handler"""
        # Log the request path for async requests
        log(f"JWT Middleware processing async request | Path: {request.path}", level="info")
        
        # Skip authentication for public paths
        if self.is_public_path(request.path):
            log(f"Public path detected (async), skipping authentication | Path: {request.path}", level="info")
            return await self.get_response(request)
        
        # Check if this is an internal service request
        if self.is_internal_service_request(request):
            log(f"Internal service request (async), skipping JWT authentication | Path: {request.path}", level="info")
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
            log(f"Token expired (async) | Path: {request.path}", level="info")
            return JsonResponse({
                'error': 'Token has expired',
                'redirect_to_login': True
            }, status=401)
        except jwt.InvalidTokenError as e:
            log(f"Invalid token (async): {str(e)} | Path: {request.path}", level="info")
            return JsonResponse({
                'error': f'Invalid token: {str(e)}',
                'redirect_to_login': True
            }, status=401)
