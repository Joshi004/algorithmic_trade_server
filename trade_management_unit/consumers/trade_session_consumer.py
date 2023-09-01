from channels.generic.websocket import WebsocketConsumer,AsyncWebsocketConsumer
from channels.layers import get_channel_layer
import json
from trade_management_unit.lib.Kite.KiteTickerUser import KiteTickerUser

class TradeSession(AsyncWebsocketConsumer):
    async def connect(self):
        print("In Consumer Now")
        self.room_name = "test_consumer"
        self.room_group_name = "trade_group"
        print("Connecting to ",self.channel_name)
        print("Group Naem is ",self.room_group_name)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({"connected":True}))
        ktu = KiteTickerUser().get_instance()
        ktu.connect()



    async def disconnect(self, close_code):
        print("Disconnected Now")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        # raise channels.exceptions.StopConsumer()



    async def receive(self, text_data=None, bytes_data=None):
        print("Data Recieverd")
        pass


    async def send_data(self, event):
        try:
            # print("in Send Data Send event for ticker",event)
            await self.send(text_data=json.dumps(event["data"]))
        except Exception as e:
            print ("error Sending reposnse via socket".e)

