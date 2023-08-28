
import logging
from kiteconnect import KiteConnect
from trade_management_unit.lib.common.EnvFile import EnvFile
import pandas as pd
from trade_management_unit.models.Instrument import Instrument
from django.utils.dateparse import parse_date



class Instruments:
    def __init__(self,params):
        self.env = EnvFile('.env')
        logging.basicConfig(level=logging.DEBUG)
        self.api_key = self.env.read("api_key")
        self.api_secret = self.env.read("api_secret")
        self.access_token = self.env.read("access_token")
       
    
    def update_instruments(self):     
        print("In update_instruments with params")
        kite = KiteConnect(api_key=self.api_key)
        kite.set_access_token(self.access_token)
        instrument_dump=kite.instruments()
        instrument_df = pd.DataFrame(instrument_dump)

        # Convert DataFrame to list of dictionaries
        instrument_dict = instrument_df.to_dict('records')

        # Create Instrument instances
        instrument_instances = [
            Instrument(
                instrument_token=instrument['instrument_token'],
                exchange_token=instrument['exchange_token'],
                trading_symbol=instrument['tradingsymbol'],
                name=instrument['name'],
                last_price=instrument['last_price'],
                expiry = parse_date(instrument['expiry']) if isinstance(instrument['expiry'], str) else None,
                strike=instrument['strike'],
                tick_size=instrument['tick_size'],
                lot_size=instrument['lot_size'],
                instrument_type=instrument['instrument_type'],
                segment=instrument['segment'],
                exchange=instrument['exchange']
            )
            for instrument in instrument_dict
        ]

        # Save all instances in one go
        Instrument.objects.bulk_create(instrument_instances)

        print("Instruments saved to database")

        
        

