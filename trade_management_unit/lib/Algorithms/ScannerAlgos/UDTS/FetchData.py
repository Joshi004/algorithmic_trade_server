import pandas as pd
from datetime import datetime, timedelta

class FetchData:
    def __init__(self):
        pass

    def sanitize_data(self, data):
        # Remove any leading or trailing spaces from column names
        data.columns = data.columns.str.strip()

        # Convert all string columns to uppercase to ensure consistency
        string_columns = data.select_dtypes(include='object').columns
        for col in string_columns:
            data[col] = data[col].str.upper()

        # Sanitize date columns
        date_columns = ['Date']
        for col in date_columns:
            data[col] = pd.to_datetime(data[col], format='%d-%b-%Y', errors='coerce')

        # Drop rows with invalid dates
        data = data.dropna(subset=date_columns)
        return data

    def fetch_candle_data(self, symbol, start_date, end_date,interval=0):
        # Convert start and end dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Read data from CSV file
        file_path = f'/Users/nareshjoshi/Documents/personal_workspace/ats_aplication/ats_server/data/{symbol}.csv'
        data = pd.read_csv(file_path)

        # Sanitize the data
        data = self.sanitize_data(data)

        # Filter rows based on start and end dates
        mask = (data['Date'] >= start_date) & (data['Date'] <= end_date)
        data = data.loc[mask]

        return data.to_dict('records')

