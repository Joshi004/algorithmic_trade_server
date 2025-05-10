from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views import View
import requests
from django.conf import settings
import json
import logging
import re

from .factory.redirect_factory import RedirectFactory

logger = logging.getLogger(__name__)

# Create your views here.

class GatewayView(View):
    """
    Main gateway view that handles all incoming requests.
    
    This class is responsible for:
    1. Authentication and authorization (to be implemented later)
    2. Routing requests to the appropriate service via the factory pattern
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.factory = RedirectFactory()
    
    def dispatch(self, request, *args, **kwargs):
        """
        Handle all incoming requests and route them to the appropriate service.
        
        Args:
            request: The Django request object
            
        Returns:
            HttpResponse: The response from the service
        """
        trace_id = request.headers.get("X-Trace-ID", "no-trace-id")
        logger.info(f"Gateway request received | Trace ID: {trace_id} | Method: {request.method} | Path: {request.path}")
        
        # Extract service prefix and path
        path_parts = self._parse_path(request.path)
        
        if not path_parts:
            logger.error(f"Invalid path format: {request.path}")
            return JsonResponse({
                "error": "Invalid path format"
            }, status=400)
        
        service_prefix, path = path_parts
        
        # TODO: Add authentication and authorization logic here
        
        # Get the appropriate connector from the factory
        connector = self.factory.get_connector(service_prefix)
        
        if not connector:
            logger.error(f"No service found for prefix: {service_prefix}")
            return JsonResponse({
                "error": f"Service '{service_prefix}' not found"
            }, status=404)
        
        # Handle the request using the connector
        return connector.handle_request(request, path)
    
    def _parse_path(self, path):
        """
        Parse the path to extract the service prefix and the actual path.
        
        Args:
            path: The full request path
            
        Returns:
            tuple: (service_prefix, path) or None if invalid format
        """
        # Extract service prefix and path using regex
        # Format: /service_prefix/path
        match = re.match(r'^/([^/]+)/(.+)$', path)
        
        if not match:
            return None
        
        service_prefix = match.group(1)
        path = match.group(2)
        
        return service_prefix, path

