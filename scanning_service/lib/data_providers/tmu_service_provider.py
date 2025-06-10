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
        self.headers = {
            'X-Internal-Service-Token': getattr(settings, 'INTERNAL_SERVICE_TOKEN', 'internal-service-secret-token-change-in-production')
        }
        
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
    
    def fetch_active_trade_sessions(self, scanning_algo_id, trading_frequency):
        """
        Fetch active trade sessions that use the specified scanner algorithm ID and frequency.
        
        Args:
            scanning_algo_id: ID of the scanning algorithm (e.g., 1 for UDTS)
            trading_frequency: Trading frequency (e.g., "5-minute", "10-minute")
                
        Returns:
            list: List of active trade session data:
                [
                    {
                        "id": session_id,
                        "user_id": user_public_id,
                        "trading_frequency": frequency,
                        "is_dummy": boolean,
                        "status": "started"
                    },
                    ...
                ]
        """
        try:
            url = f"{self.base_url}/get_active_trade_sessions/"
            params = {
                'scanning_algo_id': scanning_algo_id,
                'trading_frequency': trading_frequency
            }
            
            log(f"[Scanning] Fetching active trade sessions for scanner ID: {scanning_algo_id}, frequency: {trading_frequency}")
            log(f"[Scanning] Request URL: {url}")
            log(f"[Scanning] Request params: {params}")
            log(f"[Scanning] Request headers: {self.headers}")
            
            response = requests.get(url, params=params, headers=self.headers)
            
            log(f"[Scanning] Response status code: {response.status_code}")
            log(f"[Scanning] Response headers: {dict(response.headers)}")
            
            try:
                response_text = response.text
                log(f"[Scanning] Response text: {response_text}")
            except:
                log(f"[Scanning] Could not read response text")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    log(f"[Scanning] Response JSON parsed successfully")
                    log(f"[Scanning] Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    sessions = data.get('data', [])
                    log(f"[Scanning] Successfully fetched {len(sessions)} active trade sessions")
                    log(f"[Scanning] Sessions data: {sessions}")
                    return sessions
                except Exception as json_error:
                    log(f"[Scanning] Failed to parse JSON response: {str(json_error)}", level="error")
                    return []
            else:
                log(f"[Scanning] Failed to fetch active trade sessions from TMU, status code: {response.status_code}", level="error")
                log(f"[Scanning] Error response: {response.text}", level="error")
                return []
                
        except requests.exceptions.ConnectionError as conn_error:
            log(f"[Scanning] Failed to connect to TMU service for trade sessions: {str(conn_error)}", level="error")
            return []
        except Exception as e:
            log(f"[Scanning] Exception fetching active trade sessions from TMU: {str(e)}", level="error")
            return []
    
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