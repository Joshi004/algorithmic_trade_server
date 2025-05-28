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
            # Validate params
            if not params.get('symbol') or not params.get('exchange'):
                return {
                    'status_code': 400,
                    'error_message': 'Both "symbol" and "exchange" must be provided in params.'
                }

            symbols = [symbol.strip().upper() for symbol in params["symbol"].split(',') if symbol.strip()]
            exchange = params["exchange"].strip().upper()

            # Create instruments list in the format expected by Kite API
            instruments = [f"{exchange}:{symbol}" for symbol in symbols]
            
            # Fetch quotes for all instruments
            quotes = self.kite.quote(*instruments)

            # Prepare the response with 'data' and 'meta'
            response = {
                'data': quotes,
                'meta': {
                    'exchange': exchange,
                    'data_length': len(quotes)
                }
            }

            return response
            
        except Exception as e:
            logging.error(f"Error getting quotes: {str(e)}")
            return {
                'status_code': 500,
                'error_message': str(e)
            } 