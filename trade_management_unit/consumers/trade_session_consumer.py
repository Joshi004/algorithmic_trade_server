from channels.generic.websocket import WebsocketConsumer,AsyncWebsocketConsumer
from channels.layers import get_channel_layer
import json

class TradeSession(AsyncWebsocketConsumer):
    async def connect(self):
        print("In Consumer Now")
        self.room_name = "test_consumer"
        self.room_group_name = "trade_group"
        print("Connecting to ",self.channel_name)
        print("Group Naem is ",self.room_group_name)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()



    async def disconnect(self, close_code):
        print("Disconnected Now")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        # raise channels.exceptions.StopConsumer()



    async def receive(self, text_data=None, bytes_data=None):
        print("Data Recieverd")
        pass


    async def send_number(self, event):
        print("in Send number Send event",event)
        number = event["price"]
        print("Actuly sending now ",number)
        await self.send(text_data=json.dumps({"price": number}))

