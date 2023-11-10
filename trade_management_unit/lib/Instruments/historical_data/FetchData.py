from datetime import datetime, timedelta, time

from trade_management_unit.lib.Kite.KiteUser import KiteUser
from trade_management_unit.lib.Instruments.historical_data.Database import Database
import logging


class FetchData:
    def __init__(self):
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        self.kite = KiteUser().get_instance()   

    def fetch_hostorical_candle_data_from_kite(self,symbol, token, interval, number_of_candles, trade_date=None):
        # Initialize to_date and historical_data
        to_date = trade_date if trade_date else datetime.now()
        historical_data = []
        stored_data = self.get_stored_data(symbol,interval)
        last_stored_date = None
        if (stored_data and len(stored_data)):
            last_record_date = stored_data[-1]["date"]

        print("History from data",len(stored_data))

        iteration_count = 1
        while (len(historical_data) < number_of_candles+1 and iteration_count < 10 and to_date.year > 2019):
            iteration_count += 1
            # Skip non-trading hours (before 9:15 or after 15:30)
            if to_date.time() < time(9, 15):
                # Move to the previous trading day
                to_date = to_date.replace(hour=15, minute=30) - timedelta(days=1)
            elif to_date.time() > time(15, 30):
                # Move to the 3 30 time
                to_date = to_date.replace(hour=15, minute=30)


            # Skip weekends (Saturday and Sunday)
            while to_date.weekday() >= 5:
                # Move to the previous day
                to_date -= timedelta(days=1)

            # Calculate from_date based on the current length of historical_data
            if last_stored_date:
                from_date = last_record_date
            elif "minute" in interval:
                minutes = int(interval.replace("minute", ""))
                from_date = to_date - timedelta(minutes=minutes*(number_of_candles))
            elif interval == "day":
                from_date = to_date - timedelta(days=number_of_candles)

            # print("----- Getting Historical data symbol: ", token, " Total CAndles : ",len(historical_data),"  Time Diff: ",to_date-from_date," From: ",to_date," To: ",from_date)
            new_data = self.fetch_data_from_zerodha(token, from_date, to_date,interval)

            # Prepend new_data to historical_data
            historical_data = stored_data + new_data + historical_data
            stored_data = []

            # Update end_date for the next iteration
            to_date = from_date

        # If we fetched more data than needed, trim the excess
        total_number_of_records = len(historical_data)
        if total_number_of_records > number_of_candles:
            historical_data = historical_data[-1:-201:-1][::-1]
        print("Fetched Historical Data for ",symbol,interval)
        Database().update_historical_data(symbol,interval,historical_data)
        return historical_data

    def get_stored_data(self, symbol, interval):
        database = Database()
        # Define the table name
        table_name = f"hd__{interval}__{symbol}"

        # Check if the table exists
        if not database.table_exists(table_name):
            # If not, create the table
            database.create_hd_table(table_name)

        # Fetch all data from the table
        historical_data = database.fetch_history_data(table_name)
        return list(historical_data)

    def fetch_data_from_zerodha(self,instrument_token, start_date, end_date,interval):
        data = self.kite.historical_data(instrument_token, start_date, end_date, interval)
        return data


