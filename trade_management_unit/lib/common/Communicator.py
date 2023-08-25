from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import asyncio


class Communicator:
    def __init__(self):
        pass
    
    def send_data_to_channel_layer(self, data, group_name):
        group_name = "trade_group"
        print("In liberary sending data")
        channel_layer = get_channel_layer()
        print("Sendiong now to group",group_name)
        async_to_sync(channel_layer.group_send)(group_name, {
            "type": "send.number",
            "price": data['price'],
        })
        # print("Message sent to group")



        
        

