import logging
from django.http import JsonResponse
from .base_connector import BaseServiceConnector
import requests

logger = logging.getLogger(__name__)

class ExternalServiceConnector(BaseServiceConnector):
    """Connector for external services."""
    
    def __init__(self, service_base_url):
        """
        Initialize with the base URL for the external service.
        
        Args:
            service_base_url: The base URL for the external service
        """
        self.service_base_url = service_base_url
    
    def handle_request(self, request, path):
        """
        Forward the request to an external service.
        
        Args:
            request: The Django request object
            path: The path extracted from the URL
            
        Returns:
            HttpResponse: The response from the external service
        """
        from django.http import HttpResponse
        
        logger.info(f"ExternalServiceConnector handling path: {path} to service: {self.service_base_url}")
        
        target_url = f"{self.service_base_url}/{path}"
        
        # Forward the request with the same method, headers, and body
        headers = {key: value for key, value in request.headers.items() if key != 'Host'}
        
        try:
            logger.info(f"Forwarding to: {target_url}")
            response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.body,
                params=request.GET,
                stream=True
            )
            
            # Create a new response with the forwarded response's content
            proxy_response = HttpResponse(
                content=response.content,
                status=response.status_code,
                content_type=response.headers.get('Content-Type', 'application/json')
            )
            
            # Copy headers from the forwarded response
            for key, value in response.headers.items():
                if key.lower() not in ('content-length', 'content-encoding', 'transfer-encoding'):
                    proxy_response[key] = value
            
            return proxy_response
            
        except requests.RequestException as e:
            logger.error(f"Error forwarding request: {str(e)}", exc_info=True)
            return JsonResponse({
                "error": str(e)
            }, status=500) 