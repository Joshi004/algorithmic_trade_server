import logging
from typing import Dict, Optional
from django.conf import settings

from .connectors.base_connector import BaseServiceConnector
from .connectors.trade_management_connector import TradeManagementConnector
from .connectors.external_service_connector import ExternalServiceConnector

logger = logging.getLogger(__name__)

class RedirectFactory:
    """
    Factory class to create appropriate service connectors based on the request.
    """
    
    def __init__(self):
        """Initialize with service mappings."""
        # Initialize service map - default internal TMU service
        self.trade_management_connector = TradeManagementConnector()
        
        # Dictionary of external services: {prefix: base_url}
        # This can be loaded from settings or environment variables in the future
        self.external_services: Dict[str, str] = {}
        
        # Example external services (commented out for now)
        # self.external_services = {
        #     "auth": "http://auth-service:8001",
        #     "analytics": "http://analytics-service:8002"
        # }
    
    def get_connector(self, service_prefix: str) -> Optional[BaseServiceConnector]:
        """
        Get the appropriate connector based on the service prefix.
        
        Args:
            service_prefix: The service prefix extracted from the URL
            
        Returns:
            BaseServiceConnector: The connector instance for the service
        """
        logger.info(f"Getting connector for service prefix: {service_prefix}")
        
        # Check if this is an internal service
        if service_prefix == "tmu":
            return self.trade_management_connector
        
        # Check if this is a configured external service
        if service_prefix in self.external_services:
            base_url = self.external_services[service_prefix]
            return ExternalServiceConnector(base_url)
        
        # No connector found
        logger.error(f"No connector found for service prefix: {service_prefix}")
        return None 