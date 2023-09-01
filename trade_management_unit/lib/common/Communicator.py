from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core import serializers
import asyncio
import logging
import json



class Communicator:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.loop = asyncio.get_event_loop()
        pass
    
    def send_data_to_channel_layer(self, data, group_name):
        try:

            print("In liberary sending data")
            # print("Ticks {}".format(data))
            channel_layer = get_channel_layer()
            print("Sending now to group",group_name)
            coro = (channel_layer.group_send)(group_name, {
                "type": "send.data",
                "data": data,
            })
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        except Exception as e:
            print("Eror Occoured",e)
        print("Message sent to group")



        
        

