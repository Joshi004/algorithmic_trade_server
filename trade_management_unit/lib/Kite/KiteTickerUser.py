import logging
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
from django.core import serializers
import json
from trade_management_unit.lib.common.EnvFile import EnvFile
from trade_management_unit.lib.common.Communicator import Communicator

class KiteTickerUser:
   
    def __init__(self,instrument_tokens,communication_group,fetch_mode="quote"):
        self.env = EnvFile('.env')
        logging.basicConfig(level=logging.DEBUG)
        self.api_key = self.env.read("api_key")
        self.api_secret = self.env.read("api_secret")
        self.access_token = self.env.read("access_token")
        self.communicator = Communicator()
        self.instrument_tokens = instrument_tokens
        self.fetch_mode = fetch_mode
        self.communication_group = communication_group

    
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
            print("In OnTick")
            data = self.get_formated_ticks(ticks)
        except Exception as e:
            print ("Error geting ticks",e)
            return {'status':500,'message':'Something Went Wrong'}
        self.communicator.send_data_to_channel_layer(data, self.communication_group)


    def on_connect(self,ws,response):
        ws.subscribe(self.instrument_tokens)
        if(self.fetch_mode == "full"):
            ws.set_mode(ws.MODE_FULL,self.instrument_tokens) #Need to use Seriliser For full mode 
        elif(self.fetch_mode == "ltp"):
            ws.set_mode(ws.MODE_LTP,self.instrument_tokens) #Need to use Seriliser For full mode
        else:
            pass
         
    def on_close(self,ws,code,reason):
        print("In On Closes")
        ws.stop()

