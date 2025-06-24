import logging
from kiteconnect import KiteConnect
from integration_service.lib.broker.kite_user import KiteUser

class Trade:
    def __init__(self, user_id):
        logging.basicConfig(level=logging.DEBUG)
        self.user_id = user_id
        self.kite_user = KiteUser(user_id)
        self.kite = self.kite_user.get_instance()

    def get_quotes(self, params):
        """Get quotes for given instruments"""
        try:
            logging.debug(f"[TRADE] get_quotes called with params: {params}")
            
            # Validate params
            if not params.get('symbol') or not params.get('exchange'):
                error_msg = 'Both "symbol" and "exchange" must be provided in params.'
                logging.error(f"[TRADE] Parameter validation failed: {error_msg}")
                return {
                    'status_code': 400,
                    'error_message': error_msg
                }

            symbols = [symbol.strip().upper() for symbol in params["symbol"].split(',') if symbol.strip()]
            exchange = params["exchange"].strip().upper()
            
            logging.debug(f"[TRADE] Processed symbols: {symbols}, exchange: {exchange}")

            # Create instruments list in the format expected by Kite API
            instruments = [f"{exchange}:{symbol}" for symbol in symbols]
            logging.debug(f"[TRADE] Kite instruments format: {instruments}")
            
            # Check if kite instance is available
            if not self.kite:
                error_msg = f"Kite connection not available for user {self.user_id}"
                logging.error(f"[TRADE] {error_msg}")
                return {
                    'status_code': 500,
                    'error_message': error_msg
                }
            
            logging.debug(f"[TRADE] Making Kite API call for quotes...")
            logging.info(f"[TRADE] 🔄 CALLING KITE API: kite.quote({instruments}) for user {self.user_id}")
            
            # Fetch quotes for all instruments
            quotes = self.kite.quote(*instruments)
            
            logging.info(f"[TRADE] ✅ KITE API CALL COMPLETED: Received {type(quotes)} with {len(quotes) if isinstance(quotes, dict) else 'unknown'} items")
            
            logging.debug(f"[TRADE] Kite API response received. Type: {type(quotes)}")
            if isinstance(quotes, dict):
                logging.debug(f"[TRADE] Quote keys count: {len(quotes)}")
                logging.debug(f"[TRADE] Quote keys sample: {list(quotes.keys())[:3]}")
                
                # Log actual quote data sample
                for key in list(quotes.keys())[:2]:  # Log first 2 quotes
                    quote_data = quotes[key]
                    logging.debug(f"[TRADE] QUOTE DATA for {key}: last_price={quote_data.get('last_price')}, volume={quote_data.get('volume')}, timestamp={quote_data.get('timestamp')}")
                    logging.debug(f"[TRADE] QUOTE FIELDS for {key}: {list(quote_data.keys())}")
                    
                if len(quotes) == 0:
                    logging.warning(f"[TRADE] ⚠️ Kite API returned empty quotes for {instruments}")
            else:
                logging.warning(f"[TRADE] Unexpected quote response type: {type(quotes)}")

            # Prepare the response with 'data' and 'meta'
            response = {
                'data': quotes,
                'meta': {
                    'exchange': exchange,
                    'data_length': len(quotes) if isinstance(quotes, dict) else 0,
                    'symbols_requested': symbols,
                    'instruments_format': instruments
                }
            }
            
            logging.debug(f"[TRADE] Returning successful response with {len(quotes) if isinstance(quotes, dict) else 0} quotes")
            # Log the actual response structure being returned
            logging.debug(f"[TRADE] RESPONSE STRUCTURE: status=success, data_keys={list(quotes.keys())[:3] if isinstance(quotes, dict) else 'N/A'}, meta_keys={list(response['meta'].keys())}")
            return response
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"[TRADE] Exception in get_quotes: {error_msg}")
            logging.error(f"[TRADE] Exception type: {type(e).__name__}")
            logging.error(f"[TRADE] User ID: {self.user_id}")
            logging.error(f"[TRADE] Params: {params}")
            
            # Check if it's a Kite API specific error
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                logging.error(f"[TRADE] HTTP status from Kite: {e.response.status_code}")
                logging.error(f"[TRADE] HTTP response text: {e.response.text[:200]}")
            
            return {
                'status_code': 500,
                'error_message': error_msg
            } 