"""
TMU Service Provider for the scanning service.
Handles all communication with the Trade Management Unit (TMU) service.
"""
import requests
from django.conf import settings
from scanning_service.lib.utils.logger import log


class TMUServiceProvider:
    """
    Provides data access by calling TMU service APIs.
    """
    
    def __init__(self, user_id=None, auth_token=None):
        """
        Initialize the TMU service provider.
        
        Args:
            user_id: User ID for service identification
            auth_token: JWT token for authentication (if needed)
        """
        self.user_id = user_id
        self.auth_token = auth_token
        # Get TMU service URL from settings or use default
        self.base_url = getattr(settings, 'TMU_SERVICE_URL', 'http://localhost:8000/tmu')
        self.headers = {}
        
        if auth_token:
            self.headers['Authorization'] = f'Bearer {auth_token}'
    
    def fetch_instruments(self, search_params):
        """
        Fetch instruments list from TMU service.
        
        Args:
            search_params: Dictionary with search parameters
                - exchange: Exchange name (e.g., "NSE")
                - segment: Market segment (e.g., "NSE")
                - instrument_type: Type of instrument (e.g., "EQ")
                - page_length: Number of results per page
                - page_no: Page number (optional)
                - trading_symbol: Trading symbol to search (optional)
                - name: Instrument name to search (optional)
                
        Returns:
            dict: Instruments data with structure:
                {
                    "data": [...list of instruments...],
                    "meta": {
                        "count": total_count,
                        "num_pages": num_pages,
                        "next_page_number": next_page,
                        "previous_page_number": prev_page
                    }
                }
        """
        try:
            url = f"{self.base_url}/get_instruments/"
            
            log(f"Fetching instruments from TMU with params: {search_params}")
            response = requests.get(url, params=search_params, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                log(f"Successfully fetched {len(data.get('data', []))} instruments")
                return data
            else:
                error_msg = f"Failed to fetch instruments from TMU, status code: {response.status_code}"
                log(error_msg, level="error")
                return {"data": [], "meta": {"error": error_msg}}
                
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to TMU service. Is it running?"
            log(error_msg, level="error")
            return {"data": [], "meta": {"error": error_msg}}
        except Exception as e:
            error_msg = f"Exception fetching instruments from TMU: {str(e)}"
            log(error_msg, level="error")
            return {"data": [], "meta": {"error": error_msg}}
    

    
    def health_check(self):
        """
        Check if TMU service is accessible.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            # Try to fetch a small page of instruments as health check
            response = self.fetch_instruments({"page_length": 1})
            return "error" not in response.get("meta", {})
        except Exception as e:
            log(f"TMU health check failed: {str(e)}", level="error")
            return False 