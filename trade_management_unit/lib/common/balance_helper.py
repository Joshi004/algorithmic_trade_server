import requests
from django.conf import settings
from trade_management_unit.models.DummyAccount import DummyAccount
from trade_management_unit.models.Trade import Trade

class BalanceHelper:
    def __init__(self):
        self.integration_service_url = getattr(settings, 'INTEGRATION_SERVICE_URL', 'http://localhost:8000/integration_service')
        self.headers = {
            'X-Internal-Service-Token': getattr(settings, 'INTERNAL_SERVICE_TOKEN', 'internal-service-secret-token-change-in-production')
        }
    
    def get_current_balance_including_margin(self, user_id, dummy):
        """Get current balance including margin for a user"""
        used_margin = float(Trade.get_total_margin(user_id, dummy))
        
        if dummy:
            shown_balance = float(DummyAccount.get_attribute(user_id, "current_balance"))
            current_balance = shown_balance - used_margin
            return current_balance
        else:
            # Get available margin from integration service
            shown_balance = self._get_available_margin_from_api(user_id)
            if shown_balance is not None:
                current_balance = shown_balance - used_margin
                return current_balance
            else:
                # Fallback to 0 if API call fails
                return 0.0
    
    def _get_available_margin_from_api(self, user_id):
        """Get available margin from integration service API"""
        try:
            api_url = f"{self.integration_service_url}/get_available_margin/"
            api_params = {'user_id': user_id}
            
            response = requests.get(api_url, params=api_params, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return float(data.get('data', 0))
            
            return None
            
        except Exception as e:
            print(f"Error getting available margin: {str(e)}")
            return None 