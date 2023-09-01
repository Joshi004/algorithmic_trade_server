import logging
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
from django.core import serializers
import json
import requests
import asyncio
from trade_management_unit.lib.common.EnvFile import EnvFile
from trade_management_unit.lib.common.Communicator import Communicator

class KiteTickerUser:
   
    def __init__(self):
        self.env = EnvFile('.env')
        logging.basicConfig(level=logging.DEBUG)
        self.api_key = self.env.read("api_key")
        self.api_secret = self.env.read("api_secret")
        self.access_token = self.env.read("access_token")
        self.communicator = Communicator()
        self.loop = asyncio.get_event_loop()
    
    def get_instance(self):
        kto = KiteTicker(self.api_key,self.access_token)
        kto.on_connect = self.on_connect
        kto.on_ticks = self.on_ticks
        kto.on_close = self.on_close
        print("All handlers set")
        return kto

    def get_formated_ticks(slef,ticks):
        try: 
            # You might see that if mode is chnged to full there is no reposnse on UI wth no eror this might be coz of datetime.dateime obect that is not serlisable directly 
            # for tick in ticks:
                # if (tick["mode"] == "full"):
                #     tick = json.loads(serializers.serialize('json', tick))
            
            formated_obj = {
                'data':ticks,
                'meta':{
                'number_of_ticks' : len(ticks)
                }}
            # print("Retunrng Formated data",formated_obj)
            return formated_obj
        except Exception as e:
            print ("Error in Formating ticks",e)


    def on_ticks(self, ws, ticks):
        try:
            print("In OnTick >>>")
            data = self.get_formated_ticks(ticks)
            # print("Sending Tick to Communicator", data)
        except Exception as e:
            print ("Error geting tocks",e)
            return {'status':500,'message':'Something Went Wrong'}
        self.communicator.send_data_to_channel_layer(data, "trade_group")


    def on_connect(self,ws,response):
        print("In On Coonect")
        # ws.subscribe([738561,5633])
        ws.subscribe([738561])
        # ws.set_mode(ws.MODE_FULL,[738561,5633]) #Need to use Seriliser For full mode 

    def on_close(self,ws,code,reason):
        print("In On Closes")
        ws.stop()

