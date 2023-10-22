import pandas as pd
from datetime import datetime, timedelta
from trade_management_unit.lib.Kite.KiteUser import KiteUser
import requests

class FetchData:
    def __init__(self):
        self.kite = KiteUser().get_instance()   

    def sanitize_data(self, data):
         # Remove leading and trailing spaces from column names
        data.columns = data.columns.str.strip()
        # Convert column names to snake case
        data = data.rename(columns={
        'Open Price': 'open',
        'Close Price': 'close',
        'High Price': 'high',
        'Low Price': 'low'
    })
        data.columns = data.columns.str.lower().str.replace(' ', '_').str.replace(".","")

        # Convert all string columns to uppercase to ensure consistency
        string_columns = data.select_dtypes(include='object').columns
        for col in string_columns:
            data[col] = data[col].str.upper()
        # Sanitize date columns
        date_columns = ['date']
        for col in date_columns:
            data[col] = pd.to_datetime(data[col], format='%d-%b-%Y', errors='coerce')

        # Drop rows with invalid dates
        relevent_cols = ["date","high","low","open","close"]
        data = data.dropna(subset=relevent_cols)
        
        # Remove commas from strings and convert to float
        cols_to_convert = ['high', 'low', 'open', 'close']
        for col in cols_to_convert:
            data[col] = data[col].str.replace(',', '').astype(float) if type(data[col]) == "str" else data[col]
        return data

    def fetch_candle_data(self, symbol, start_date, end_date,interval=0):
        # Convert start and end dates to datetime objects
        if(type(start_date) == type(end_date) == "str"):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Read data from CSV file
        file_path = f'/Users/nareshjoshi/Documents/personal_workspace/ats_aplication/algorithmic_trade_server/data/{symbol}.csv'
        
        data = pd.read_csv(file_path)

        # Sanitize the data
        data = self.sanitize_data(data)

        # Filter rows based on start and end dates
        mask = (data['date'] >= start_date) & (data['date'] <= end_date)
        data = data.loc[mask]
        return data.to_dict('records')

    def fetch_from_nse(self, symbol, start_date, end_date):
        # Convert dates to the required format
        start_date = start_date.strftime('%d-%m-%Y')
        end_date = end_date.strftime('%d-%m-%Y')

        # Capitalize the symbol
        symbol = symbol.upper()

        # Construct the URL
        url = f"https://www.nseindia.com/api/historical/securityArchives?from={start_date}&to={end_date}&symbol={symbol}&dataType=priceVolumeDeliverable&series=ALL"
        
        # Fetch data from NSE
        response =  requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to fetch data from NSE. Status code: {response.status_code}")
            return None


    def fetch_data_from_zerodha(self,instrument_token,from_date,to_date,interval):
        historical_data  = self.kite.historical_data(instrument_token,from_date,to_date,interval)
        return historical_data
