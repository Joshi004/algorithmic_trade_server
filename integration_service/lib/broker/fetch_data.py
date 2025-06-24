from datetime import timedelta, time
import re
from integration_service.lib.broker.kite_user import KiteUser
from integration_service.Constants.IntegrationConstants import FREQUENCY_MAPPING
from kiteconnect.exceptions import NetworkException
from integration_service.lib.utils.logger import log
import time as tm

class FetchData:
    def __init__(self, user_id):
        self.user_id = user_id
        self.kite_user = KiteUser(user_id)
        self.kite = self.kite_user.get_instance()

    def fetch_historical_data_for_client(self, symbol, token, interval, number_of_candles, trade_date=None):
        """Public method for external API consumption"""
        # Log the input parameters
        log(f"[INTEGRATION_FETCH] Starting historical data fetch for symbol={symbol}, token={token}, interval={interval}, candles={number_of_candles}, trade_date={trade_date}")
        
        api_success = True
        api_error_message = None
        
        try:
            history_data = self.fetch_historical_candle_data_from_kite(symbol, token, interval, number_of_candles, trade_date)
        except Exception as e:
            # Mark as API failure when there's an exception
            api_success = False
            api_error_message = str(e)
            history_data = []
            log(f"[INTEGRATION_FETCH] ❌ API failure for {symbol}: {str(e)}", level="error")
        
        # Log the result
        log(f"[INTEGRATION_FETCH] Historical data fetched for {symbol}: {len(history_data)} candles returned")
        if len(history_data) == 0:
            if api_success:
                log(f"[INTEGRATION_FETCH] ⚠️ ZERO data returned from Kite for {symbol} (token={token}, interval={interval}) - API succeeded but no data available", level="warning")
            else:
                log(f"[INTEGRATION_FETCH] ❌ ZERO data returned from Kite for {symbol} (token={token}, interval={interval}) - API failed: {api_error_message}", level="error")
        else:
            # Log sample data
            first_candle = history_data[0] if history_data else None
            last_candle = history_data[-1] if history_data else None
            log(f"[INTEGRATION_FETCH] Sample data for {symbol}: first_candle={first_candle}, last_candle={last_candle}")
        
        response = {
            "data": history_data,
            "meta": {
                "size": len(history_data),
                "api_success_status": api_success,
                "api_error_message": api_error_message if not api_success else None
            }
        }
        return response

    def fetch_historical_candle_data_from_kite(self, symbol, token, interval, number_of_candles, trade_date=None):
        """Internal method to fetch historical data from Kite"""
        # Note: Database storage functionality has been simplified for integration service
        # The original Database class functionality should be implemented if needed
        
        try:
            # For simplicity, we'll directly fetch from Kite without local database caching
            # This can be enhanced later with proper database integration
            
            # Calculate date range
            if trade_date:
                to_date = trade_date
            else:
                from datetime import datetime
                to_date = datetime.now()
            
            # Calculate from_date based on interval and number of candles
            if "-minute" in interval:
                # Handle new format (5-minute)
                minute_str = interval.replace("-minute", "")
                minutes = int(minute_str) if minute_str else 1
                from_date = to_date - timedelta(minutes=minutes * number_of_candles)
                from_date =  datetime.now() - timedelta(days=50)  # Hard-coded from date to be removed after testing
            elif interval == "1-day" or interval == "day":
                from_date = to_date - timedelta(days=number_of_candles)
                from_date =  datetime.now() - timedelta(days=50)  # Hard-coded from date to be removed after testing
            else:
                # Default fallback
                from_date = to_date - timedelta(days=number_of_candles)
            
            # Log the calculated date range
            log(f"[INTEGRATION_FETCH] Date range calculated for {symbol}: from_date={from_date}, to_date={to_date}, interval={interval}")
            
            # Fetch data from Zerodha
            historical_data = self.fetch_data_from_zerodha(token, from_date, to_date, interval)
            
            # Log raw Kite response
            log(f"[INTEGRATION_FETCH] Raw Kite response for {symbol}: received {len(historical_data)} candles")
            
            # Limit the data to requested number of candles
            if len(historical_data) > number_of_candles:
                historical_data = historical_data[-number_of_candles:]
                log(f"[INTEGRATION_FETCH] Data limited to {number_of_candles} candles for {symbol}")
            
            return historical_data
            
        except Exception as e:
            log(f"[INTEGRATION_FETCH] ❌ Error fetching historical data for {symbol}: {str(e)}", level="error")
            raise

    def fetch_data_from_zerodha(self, instrument_token, start_date, end_date, interval):
        """Fetch data directly from Zerodha with rate limiting"""
        # Convert TMU frequency format to Zerodha API format
        zerodha_interval = FREQUENCY_MAPPING.get(interval, interval)
        
        # Log the API call parameters
        log(f"[KITE_API_CALL] Making Kite API call: token={instrument_token}, start_date={start_date}, end_date={end_date}, original_interval={interval}, zerodha_interval={zerodha_interval}")
        
        # Additional validation logging
        log(f"[KITE_API_CALL] Token type: {type(instrument_token)}, Token value: {instrument_token}")
        log(f"[KITE_API_CALL] Start date type: {type(start_date)}, Start date: {start_date}")
        log(f"[KITE_API_CALL] End date type: {type(end_date)}, End date: {end_date}")
        log(f"[KITE_API_CALL] Interval mapping: {interval} -> {zerodha_interval}")
        
        while True:
            try:
                # Make the actual Kite API call
                log(f"[KITE_API_CALL] About to call: self.kite.historical_data({instrument_token}, {start_date}, {end_date}, '{zerodha_interval}')")
                data = self.kite.historical_data(instrument_token, start_date, end_date, zerodha_interval)
                log(f"[KITE_API_CALL] Kite API call completed successfully")
                
                # Log detailed response information
                log(f"[KITE_API_RESPONSE] Received response for token {instrument_token}: {len(data)} candles")
                
                if len(data) == 0:
                    # Log detailed info when no data is returned
                    log(f"[KITE_API_RESPONSE] ⚠️ ZERO candles returned from Kite API", level="warning")
                    log(f"[KITE_API_RESPONSE] Token: {instrument_token}", level="warning")
                    log(f"[KITE_API_RESPONSE] Date range: {start_date} to {end_date}", level="warning")
                    log(f"[KITE_API_RESPONSE] Interval: {zerodha_interval} (original: {interval})", level="warning")
                    log(f"[KITE_API_RESPONSE] This could indicate: expired instrument, invalid token, no trading data for this period, or unsupported instrument type", level="warning")
                    
                    # Try to get some info about the instrument
                    try:
                        # Note: We don't call instrument lookup here to avoid additional API calls
                        # But we can log that this might be an expired option
                        if str(instrument_token).startswith('16') or str(instrument_token).startswith('17'):
                            log(f"[KITE_API_RESPONSE] Token {instrument_token} appears to be an option contract (starts with 16/17) - likely expired", level="warning")
                    except Exception as e:
                        log(f"[KITE_API_RESPONSE] Error during token analysis: {str(e)}", level="error")
                        
                else:
                    # Log sample data when data is available
                    first_candle = data[0] if data else None
                    last_candle = data[-1] if len(data) > 1 else None
                    log(f"[KITE_API_RESPONSE] Sample data: first={first_candle}, last={last_candle}")
                
                return data
                
            except NetworkException as e:
                if 'Too many requests' in str(e):
                    log(f"[KITE_API_RESPONSE] Rate limit exceeded for token {instrument_token}. Retrying after 1 second...", level="warning")
                    tm.sleep(1)
                else:
                    log(f"[KITE_API_RESPONSE] ❌ Network error for token {instrument_token}: {str(e)}", level="error")
                    raise e
            except Exception as e:
                log(f"[KITE_API_RESPONSE] ❌ Error fetching data from Zerodha for token {instrument_token}: {str(e)}", level="error")
                log(f"[KITE_API_RESPONSE] Parameters: start_date={start_date}, end_date={end_date}, interval={zerodha_interval}", level="error")
                log(f"[KITE_API_RESPONSE] Exception type: {type(e).__name__}", level="error")
                log(f"[KITE_API_RESPONSE] Exception args: {e.args}", level="error")
                raise e

 