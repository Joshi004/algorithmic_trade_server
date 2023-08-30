
import logging
from kiteconnect import KiteConnect
from trade_management_unit.lib.common.EnvFile import EnvFile
from trade_management_unit.lib.Kite.KiteUser import KiteUser
from trade_management_unit.models.Instrument import Instrument

class Trade:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.kite = KiteUser().get_instance()      

    def validate_params(self, params):
        # Check if 'symbol' and 'exchange' are present in params
        if not all(key in params for key in ('symbol', 'exchange')):
            return {
                'status_code': 400,
                'error_message': 'Both "symbol" and "exchange" must be provided in params.'
            }

        symbols = [symbol.strip().upper() for symbol in params["symbol"].split(',') if symbol.strip()]  # Capitalizing the trading symbols, excluding empty symbols
        exchange = params["exchange"].strip().upper()  # Capitalizing the exchange

        # Check if 'symbols' and 'exchange' are valid fields in the Instrument model
        for symbol in symbols:
            if not Instrument.objects.filter(trading_symbol=symbol, exchange=exchange).exists():
                return {
                    'status_code': 400,
                    'error_message': f'The symbol "{symbol}" does not exist in the "{exchange}" exchange.'
                }

        return symbols, exchange

    def get_quotes(self, params):
        validation_result = self.validate_params(params)
        if isinstance(validation_result, dict):  # If validation failed, return the error message
            return validation_result

        symbols, exchange = validation_result


        instruments = [f"{exchange}:{symbol}" for symbol in symbols]  # Creating a list of instruments in the format accepted by Kite API
        quotes = self.kite.quote(*instruments)  # Fetching quotes for all instruments

        # Prepare the response with 'data' and 'meta'
        response = {
            'data': quotes,
            'meta': {
                'exchange': exchange,
                'data_length': len(quotes)
            }
        }

        return response


        
        

