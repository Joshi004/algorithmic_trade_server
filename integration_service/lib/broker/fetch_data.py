from datetime import timedelta, time
import re
from integration_service.lib.broker.kite_user import KiteUser
from kiteconnect.exceptions import NetworkException
import logging
import time as tm

class FetchData:
    def __init__(self, user_id):
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        self.user_id = user_id
        self.kite_user = KiteUser(user_id)
        self.kite = self.kite_user.get_instance()

    def fetch_historical_data_for_client(self, symbol, token, interval, number_of_candles, trade_date=None):
        """Public method for external API consumption"""
        history_data = self.fetch_historical_candle_data_from_kite(symbol, token, interval, number_of_candles, trade_date)
        response = {
            "data": history_data,
            "meta": {
                "size": len(history_data)
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
            if "minute" in interval:
                # Handle both old format (5minute) and new format (5-minute)
                if "-minute" in interval:
                    minute_str = interval.replace("-minute", "")
                    minutes = int(minute_str) if minute_str else 1
                else:
                    minute_str = interval.replace("minute", "")
                    minutes = int(minute_str) if minute_str else 1
                from_date = to_date - timedelta(minutes=minutes * number_of_candles)
            elif interval == "1-day" or interval == "day":
                from_date = to_date - timedelta(days=number_of_candles)
            else:
                # Default fallback
                from_date = to_date - timedelta(days=number_of_candles)
            
            # Fetch data from Zerodha
            historical_data = self.fetch_data_from_zerodha(token, from_date, to_date, interval)
            
            # Limit the data to requested number of candles
            if len(historical_data) > number_of_candles:
                historical_data = historical_data[-number_of_candles:]
            
            return historical_data
            
        except Exception as e:
            logging.error(f"Error fetching historical data: {str(e)}")
            raise

    def fetch_data_from_zerodha(self, instrument_token, start_date, end_date, interval):
        """Fetch data directly from Zerodha with rate limiting"""
        while True:
            try:
                data = self.kite.historical_data(instrument_token, start_date, end_date, interval)
                return data
            except NetworkException as e:
                if 'Too many requests' in str(e):
                    logging.warning("Rate limit exceeded. Retrying after 1 second...")
                    tm.sleep(1)
                else:
                    logging.error(f"Network error: {str(e)}")
                    raise e
            except Exception as e:
                logging.error(f"Error fetching data from Zerodha: {str(e)}")
                raise e

    def separate_time(self, s):
        """Helper method to parse time intervals"""
        # If the string is empty or None, return 1 and None
        if not s:
            return 1, None

        # Use regex to find the number and unit in the string
        match = re.match(r'(\d*)(\D*)', s.strip())

        # If there's no match, return 1 and None
        if not match:
            return 1, None

        # Get the number and unit from the match
        number, unit = match.groups()

        # If the number is empty, assume it's 1
        if not number:
            number = '1'

        # Return the number as an int and the unit
        return int(number), str(unit) + "s" 