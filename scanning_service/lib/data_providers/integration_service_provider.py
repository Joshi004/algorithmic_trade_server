"""
Data provider for the scanning service that calls integration service APIs.
"""
import time
import requests
from django.conf import settings
from scanning_service.lib.utils.logger import log
from integration_service.lib.common.error_classifier import is_temporary_error


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
        self.base_url = getattr(settings, 'INTEGRATION_SERVICE_URL', 'http://localhost:8000/integration')
        self.headers = {
            'X-Internal-Service-Token': getattr(settings, 'INTERNAL_SERVICE_TOKEN', 'internal-service-secret-token-change-in-production')
        }
        
    def get_quotes(self, symbol, exchange="NSE"):
        """
        Get quotes for a symbol from integration service.
        
        Args:
            symbol: Trading symbol
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
                    
                log(f"Fetching quotes for {symbol} from {exchange} (attempt {attempt + 1}/{max_attempts})")
                
                # Debug log the full request details
                log(f"[DEBUG] Request URL: {url}", level="debug")
                log(f"[DEBUG] Request params: {params}", level="debug")
                log(f"[DEBUG] Request headers: {self.headers}", level="debug")
                
                response = requests.get(url, params=params, headers=self.headers)
                
                # Debug log the response details
                log(f"[DEBUG] Response status: {response.status_code}", level="debug")
                log(f"[DEBUG] Response headers: {dict(response.headers)}", level="debug")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        log(f"[DEBUG] Response JSON status: {data.get('status', 'N/A')}", level="debug")
                        log(f"[DEBUG] Response JSON keys: {list(data.keys())}", level="debug")
                        
                        if data.get("status") == "success":
                            quotes_data = data.get("data", {})
                            log(f"[DEBUG] Quotes data keys count: {len(quotes_data)}", level="debug")
                            if quotes_data:
                                # Log first quote key as sample
                                first_key = next(iter(quotes_data), None)
                                if first_key:
                                    log(f"[DEBUG] Sample quote key: {first_key}", level="debug")
                                    sample_quote = quotes_data[first_key]
                                    log(f"[DEBUG] Sample quote fields: {list(sample_quote.keys())[:10]}", level="debug")
                                    # Log actual quote values
                                    log(f"[DEBUG] RECEIVED QUOTE DATA for {first_key}: last_price={sample_quote.get('last_price')}, volume={sample_quote.get('volume')}, timestamp={sample_quote.get('timestamp')}", level="debug")
                                    log(f"[DEBUG] RECEIVED QUOTE DETAILS for {first_key}: buy_qty={sample_quote.get('buy_quantity')}, sell_qty={sample_quote.get('sell_quantity')}, avg_price={sample_quote.get('average_price')}", level="debug")
                            else:
                                log(f"[WARNING] Integration service returned success but empty quotes data for {symbol}", level="warning")
                            return {"data": data.get("data", {}), "meta": data.get("meta", {})}
                        else:
                            error_msg = data.get('error', 'Unknown error')
                            log(f"[ERROR] API returned error status: {error_msg}", level="error")
                            log(f"[DEBUG] Full error response: {data}", level="debug")
                            if not is_temporary_error(error_msg) or attempt == max_attempts - 1:
                                return {"data": {}, "meta": {"error": error_msg}}
                    except ValueError as json_error:
                        log(f"[ERROR] Failed to parse JSON response: {str(json_error)}", level="error")
                        log(f"[DEBUG] Raw response text: {response.text[:500]}", level="debug")
                        if attempt == max_attempts - 1:
                            return {"data": {}, "meta": {"error": "Invalid JSON response"}}
                else:
                    log(f"[ERROR] Failed to get quotes, status code: {response.status_code}", level="error")
                    log(f"[DEBUG] Error response text: {response.text[:500]}", level="debug")
                    if not is_temporary_error(response.status_code) or attempt == max_attempts - 1:
                        return {"data": {}, "meta": {"error": f"HTTP {response.status_code}"}}
                        
            except Exception as e:
                log(f"Exception getting quotes (attempt {attempt + 1}/{max_attempts}): {str(e)}", level="error")
                if not is_temporary_error(str(e)) or attempt == max_attempts - 1:
                    return {"data": {}, "meta": {"error": str(e)}}
            
            # Wait before retry if not the last attempt
            if attempt < max_attempts - 1:
                delay = base_delay * (multiplier ** attempt)
                time.sleep(delay)
        
        return {"data": {}, "meta": {"error": "Max retries exceeded"}}
    
    def fetch_historical_candle_data_from_kite(self, symbol, token, interval, number_of_candles, trade_date=None):
        """
        Fetch historical candle data from integration service.
        
        Args:
            symbol: Trading symbol
            token: Instrument token
            interval: Time interval (e.g., "5-minute", "1-day")
            number_of_candles: Number of candles to fetch
            trade_date: Optional trade date
            
        Returns:
            list: Historical candle data
        """
        max_attempts = 3
        base_delay = 1.0
        multiplier = 2
        
        for attempt in range(max_attempts):
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
                    
                log(f"[SCAN] 📊 Fetching historical data for {symbol}, interval: {interval}, candles: {number_of_candles} (attempt {attempt + 1}/{max_attempts})")
                
                # Enhanced debugging - log instrument details
                log(f"[SCAN_DEBUG] Instrument details: symbol={symbol}, token={token}, type={'Option' if 'HP' in symbol else 'Equity' if symbol.isalpha() else 'Unknown'}")
                
                # Debug log the full request details
                log(f"[DEBUG] Historical data request URL: {url}", level="debug")
                log(f"[DEBUG] Historical data request params: {params}", level="debug")
                
                response = requests.get(url, params=params, headers=self.headers)
                
                # Debug log the response details
                log(f"[DEBUG] Historical data response status: {response.status_code}", level="debug")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        log(f"[DEBUG] Historical data response JSON status: {data.get('status', 'N/A')}", level="debug")
                        
                        if data.get("status") == "success":
                            candle_data = data.get("data", [])
                            meta_data = data.get("meta", {})
                            api_success = meta_data.get("api_success_status", True)
                            api_error_message = meta_data.get("api_error_message")
                            
                            if candle_data and len(candle_data) > 0:
                                log(f"[SCAN] ✅ Successfully fetched {len(candle_data)} candles for {symbol} {interval}")
                                return candle_data
                            else:
                                # Check if this is API success with zero data (legitimate) or API failure
                                if api_success:
                                    # This is a legitimate case - API succeeded but no data available (e.g., expired instrument)
                                    log(f"[SCAN] ⚠️ No data returned for {symbol} {interval} - API succeeded but instrument has no data (likely expired)", level="warning")
                                    log(f"[DEBUG] Full API response: {data}", level="debug")
                                    # Return empty data immediately, don't retry for legitimate zero-data cases
                                    return []
                                else:
                                    # This is an API failure - should log error and potentially retry
                                    log(f"[SCAN] ❌ API failure for {symbol} {interval}: {api_error_message or 'Unknown API error'}", level="error")
                                    log(f"[DEBUG] Full API response: {data}", level="debug")
                                    if attempt == max_attempts - 1:
                                        return []
                        else:
                            error_msg = data.get('error', 'Unknown error')
                            log(f"[SCAN] ❌ API error for {symbol} {interval}: {error_msg}", level="error")
                            log(f"[DEBUG] Full error response: {data}", level="debug")
                            if not is_temporary_error(error_msg) or attempt == max_attempts - 1:
                                return []
                    except ValueError as json_error:
                        log(f"[SCAN] ❌ JSON parse error for {symbol} {interval}: {str(json_error)}", level="error")
                        log(f"[DEBUG] Raw response text: {response.text[:500]}", level="debug")
                        if attempt == max_attempts - 1:
                            return []
                else:
                    log(f"[SCAN] ❌ HTTP error for {symbol} {interval}, status code: {response.status_code}", level="error")
                    log(f"[DEBUG] Error response text: {response.text[:500]}", level="debug")
                    if not is_temporary_error(response.status_code) or attempt == max_attempts - 1:
                        return []
                        
            except requests.exceptions.ConnectionError as e:
                log(f"[SCAN] ❌ Connection error for {symbol} {interval} (attempt {attempt + 1}/{max_attempts}): {str(e)}", level="error")
                if attempt == max_attempts - 1:
                    return []
            except requests.exceptions.Timeout as e:
                log(f"[SCAN] ❌ Timeout error for {symbol} {interval} (attempt {attempt + 1}/{max_attempts}): {str(e)}", level="error")
                if attempt == max_attempts - 1:
                    return []
            except Exception as e:
                log(f"[SCAN] ❌ Unexpected error for {symbol} {interval} (attempt {attempt + 1}/{max_attempts}): {str(e)}", level="error")
                if not is_temporary_error(str(e)) or attempt == max_attempts - 1:
                    return []
            
            # Wait before retry if not the last attempt
            if attempt < max_attempts - 1:
                delay = base_delay * (multiplier ** attempt)
                log(f"[SCAN] ⏳ Retrying {symbol} {interval} in {delay}s...", level="warning")
                time.sleep(delay)
        
        log(f"[SCAN] ❌ Max retries exceeded for {symbol} {interval} - returning empty data", level="error")
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