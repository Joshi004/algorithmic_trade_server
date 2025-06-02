"""
Data provider for the scanning service that calls integration service APIs.
"""
import requests
from django.conf import settings
from scanning_service.lib.utils.logger import log


class IntegrationServiceProvider:
    """
    Provides data access by calling integration service APIs.
    """
    
    def __init__(self, user_id=None):
        """
        Initialize the data provider.
        
        Args:
            user_id: User ID for authentication (if needed)
        """
        self.user_id = user_id
        self.base_url = getattr(settings, 'INTEGRATION_SERVICE_URL', 'http://localhost:8000/integration_service')
        
    def get_quotes(self, symbol, exchange="NSE"):
        """
        Get quotes for a symbol from integration service.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name (default: NSE)
            
        Returns:
            dict: Quote data with structure {"data": {...}, "meta": {...}}
        """
        try:
            url = f"{self.base_url}/get_quotes/"
            params = {
                "symbol": symbol,
                "exchange": exchange
            }
            
            if self.user_id:
                params["user_id"] = self.user_id
                
            log(f"Fetching quotes for {symbol} from {exchange}")
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return {"data": data.get("data", {}), "meta": data.get("meta", {})}
                else:
                    log(f"Error getting quotes: {data.get('error')}", level="error")
                    return {"data": {}, "meta": {"error": data.get("error")}}
            else:
                log(f"Failed to get quotes, status code: {response.status_code}", level="error")
                return {"data": {}, "meta": {"error": f"HTTP {response.status_code}"}}
                
        except Exception as e:
            log(f"Exception getting quotes: {str(e)}", level="error")
            return {"data": {}, "meta": {"error": str(e)}}
    
    def fetch_historical_candle_data_from_kite(self, symbol, token, interval, number_of_candles, trade_date=None):
        """
        Fetch historical candle data from integration service.
        
        Args:
            symbol: Trading symbol
            token: Instrument token
            interval: Time interval (e.g., "5minute", "day")
            number_of_candles: Number of candles to fetch
            trade_date: Optional trade date
            
        Returns:
            list: Historical candle data
        """
        try:
            url = f"{self.base_url}/get_historical_data/"
            params = {
                "symbol": symbol,
                "token": token,
                "interval": interval,
                "number_of_candles": number_of_candles
            }
            
            if self.user_id:
                params["user_id"] = self.user_id
                
            if trade_date:
                params["trade_date"] = trade_date.isoformat() if hasattr(trade_date, 'isoformat') else str(trade_date)
                
            log(f"Fetching historical data for {symbol}, interval: {interval}, candles: {number_of_candles}")
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return data.get("data", [])
                else:
                    log(f"Error getting historical data: {data.get('error')}", level="error")
                    return []
            else:
                log(f"Failed to get historical data, status code: {response.status_code}", level="error")
                return []
                
        except Exception as e:
            log(f"Exception getting historical data: {str(e)}", level="error")
            return []
    
    def fetch_instruments(self, search_params):
        """
        Fetch instruments list. 
        Note: This might need a separate API endpoint in integration service or TMU.
        
        Args:
            search_params: Dictionary with search parameters
            
        Returns:
            dict: Instruments data
        """
        # TODO: This needs to be implemented based on where instrument data lives
        # For now, returning empty response
        log("fetch_instruments not yet implemented - needs API endpoint", level="warning")
        return {"data": [], "meta": {"error": "Not implemented"}} 