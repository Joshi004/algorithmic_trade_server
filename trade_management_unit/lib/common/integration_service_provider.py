"""
Data provider for the trade management unit that calls integration service APIs.
"""
import time
import requests
from django.conf import settings
import logging
from integration_service.lib.common.error_classifier import is_temporary_error
from integration_service.lib.common.system_user_utils import get_system_user_id


class IntegrationServiceProvider:
    """
    Provides data access by calling integration service APIs.
    """
    
    def __init__(self, user_id=None):
        """
        Initialize the data provider.
        
        Args:
            user_id: User ID for authentication. Use "system" for system-level operations.
        """
        # Handle system user ID resolution
        if user_id == "system":
            self.user_id = get_system_user_id()
            logging.info(f"Using system user ID: {self.user_id}")
        else:
            self.user_id = user_id
            
        self.base_url = getattr(settings, 'INTEGRATION_SERVICE_URL', 'http://localhost:8000/integration')
        self.headers = {
            'X-Internal-Service-Token': getattr(settings, 'INTERNAL_SERVICE_TOKEN', 'internal-service-secret-token-change-in-production')
        }
        
    def get_quotes(self, symbol, exchange="NSE"):
        """
        Get quotes for a symbol from integration service.
        
        Args:
            symbol: Trading symbol (can be comma-separated for multiple symbols)
            exchange: Exchange name (default: NSE)
            
        Returns:
            dict: Quote data with structure {"data": {...}, "meta": {...}}
        """
        max_attempts = 3
        base_delay = 1.0
        multiplier = 2
        
        for attempt in range(max_attempts):
            try:
                url = f"{self.base_url}/get_quotes/"
                params = {
                    "symbol": symbol,
                    "exchange": exchange
                }
                
                if self.user_id:
                    params["user_id"] = self.user_id
                    
                logging.debug(f"Fetching quotes for {symbol} from {exchange} (attempt {attempt + 1}/{max_attempts})")
                response = requests.get(url, params=params, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        return {
                            'data': data['data'],
                            'meta': data['meta']
                        }
                    else:
                        error_msg = data.get('error', 'Unknown error from integration service')
                        logging.error(f"Error getting quotes: {error_msg}")
                        if not is_temporary_error(error_msg) or attempt == max_attempts - 1:
                            return {
                                'status_code': 500,
                                'error_message': error_msg
                            }
                else:
                    logging.error(f"Failed to get quotes, status code: {response.status_code}")
                    if not is_temporary_error(response.status_code) or attempt == max_attempts - 1:
                        return {
                            'status_code': response.status_code,
                            'error_message': f'Integration service error: {response.text}'
                        }
                        
            except requests.exceptions.RequestException as e:
                logging.error(f"Error calling integration service (attempt {attempt + 1}/{max_attempts}): {str(e)}")
                if not is_temporary_error(str(e)) or attempt == max_attempts - 1:
                    return {
                        'status_code': 500,
                        'error_message': f'Failed to connect to integration service: {str(e)}'
                    }
            except Exception as e:
                logging.error(f"Unexpected error (attempt {attempt + 1}/{max_attempts}): {str(e)}")
                return {
                    'status_code': 500,
                    'error_message': f'Unexpected error: {str(e)}'
                }
            
            # Wait before retry if not the last attempt
            if attempt < max_attempts - 1:
                delay = base_delay * (multiplier ** attempt)
                time.sleep(delay)
        
        return {
            'status_code': 500,
            'error_message': 'Max retries exceeded'
        }
    
    def get_instruments(self):
        """
        Get all instruments from integration service.
        
        Returns:
            dict: Instruments data with structure {"status": "success", "data": [...], "meta": {...}}
        """
        max_attempts = 3
        base_delay = 1.0
        multiplier = 2
        
        for attempt in range(max_attempts):
            try:
                url = f"{self.base_url}/get_instruments/"
                params = {}
                
                if self.user_id:
                    params["user_id"] = self.user_id
                    
                logging.debug(f"Fetching instruments (attempt {attempt + 1}/{max_attempts})")
                response = requests.get(url, params=params, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        return data
                    else:
                        error_msg = data.get('error', 'Unknown error from integration service')
                        logging.error(f"Error getting instruments: {error_msg}")
                        if not is_temporary_error(error_msg) or attempt == max_attempts - 1:
                            return {
                                'status': 'error',
                                'error': error_msg
                            }
                else:
                    logging.error(f"Failed to get instruments, status code: {response.status_code}")
                    if not is_temporary_error(response.status_code) or attempt == max_attempts - 1:
                        return {
                            'status': 'error',
                            'error': f'Integration service error: {response.text}'
                        }
                        
            except requests.exceptions.RequestException as e:
                logging.error(f"Error calling integration service (attempt {attempt + 1}/{max_attempts}): {str(e)}")
                if not is_temporary_error(str(e)) or attempt == max_attempts - 1:
                    return {
                        'status': 'error',
                        'error': f'Failed to connect to integration service: {str(e)}'
                    }
            except Exception as e:
                logging.error(f"Unexpected error (attempt {attempt + 1}/{max_attempts}): {str(e)}")
                return {
                    'status': 'error',
                    'error': f'Unexpected error: {str(e)}'
                }
            
            # Wait before retry if not the last attempt
            if attempt < max_attempts - 1:
                delay = base_delay * (multiplier ** attempt)
                time.sleep(delay)
        
        return {
            'status': 'error',
            'error': 'Max retries exceeded'
        } 