from abc import ABC, abstractmethod

class BaseServiceConnector(ABC):
    """Abstract base class for all service connectors."""
    
    @abstractmethod
    def handle_request(self, request, path):
        """
        Handle the incoming request by routing it to the appropriate service.
        
        Args:
            request: The Django request object
            path: The path extracted from the URL
            
        Returns:
            HttpResponse: The response from the service
        """
        pass 