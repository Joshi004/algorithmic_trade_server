"""
Instruments library for integration service.
Handles fetching instruments data from Kite API.
"""
from integration_service.lib.broker.fetch_data import FetchData


class InstrumentsProvider:
    """
    Provides instruments data from Kite API.
    """
    
    def __init__(self, user_id):
        """
        Initialize the instruments provider.
        
        Args:
            user_id: User ID for Kite API access
        """
        self.user_id = user_id
        self.fetch_data = FetchData(user_id)
    
    def get_all_instruments(self):
        """
        Fetch all instruments from Kite API.
        
        Returns:
            dict: Response with instruments data and status
        """
        try:
            # Get the kite instance from FetchData
            kite_instance = self.fetch_data.kite
            
            if not kite_instance:
                return {
                    "status": "error",
                    "error": "Unable to get Kite connection for user",
                    "data": []
                }
            
            # Fetch instruments from Kite API
            instruments_data = kite_instance.instruments()
            
            return {
                "status": "success",
                "data": instruments_data,
                "meta": {
                    "count": len(instruments_data),
                    "source": "kite_api"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "data": []
            } 