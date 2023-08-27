
import logging
from kiteconnect import KiteConnect
from trade_management_unit.lib.common.EnvFile import EnvFile


class Trade:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.api_key = self.env.read("api_key")
       
    
    def get_instruments(self):     
        print("In get instrument")
        kite = KiteConnect(api_key=self.api_key)
        data=kite.instruments()
        print("Got The instrument",len(data))

        return data

        # print("Message sent to group")



        
        

