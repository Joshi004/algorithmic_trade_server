from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core import serializers
import asyncio
import logging
import json
import datetime
from enum import Enum


class Communicator:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.loop = asyncio.get_event_loop()
        pass
    
    def make_json_serializable(self,data):
        # To improve performance do not use this but fix the data type at source only
        if isinstance(data, dict):
            return {k: self.make_json_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.make_json_serializable(v) for v in data]
        elif isinstance(data, datetime.datetime):
            return data.isoformat()
        elif isinstance(data, Enum):
            return data.value
        else:
            return data

    def send_data_to_channel_layer(self, data, group_name):
        try:
            data = self.make_json_serializable(data)
            channel_layer = get_channel_layer()
            coro = (channel_layer.group_send)(group_name, {
                "type": "send.data",
                "data": data,
            })
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        except Exception as e:
            print("Eror Occoured",e)



        
        

