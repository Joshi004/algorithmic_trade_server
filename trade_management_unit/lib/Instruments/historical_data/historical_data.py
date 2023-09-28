from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.FetchData import FetchData

class HistoricalData:
    def __init__(self):
        pass

    def fetch_data(self, req_params):
        # Extract the required parameters from req_params
        symbol = req_params.get('symbol')
        start_date = req_params.get('start_date')
        end_date = req_params.get('end_date')
        interval = req_params.get('interval')

        # Use the library to fetch the data
        historical_data = FetchData().fetch_candle_data(symbol, start_date, end_date, interval)
        res = {
            "data":historical_data,
            "meta": {"size":len(historical_data)}
        }
        return res
