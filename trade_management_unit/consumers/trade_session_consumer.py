from channels.generic.websocket import WebsocketConsumer,AsyncWebsocketConsumer
from channels.layers import get_channel_layer
import json
from trade_management_unit.lib.Kite.KiteTickerUser import KiteTickerUser

class TradeSession(AsyncWebsocketConsumer):
    async def connect(self):
        instrument_tokens = [738561]
        communication_group = "trade_group"
        print("In Consumer Now")
        self.room_group_name = communication_group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()    
        ktu = KiteTickerUser(instrument_tokens,communication_group).get_instance()
        ktu.connect()
        await self.send(text_data=json.dumps({"connected":True}))



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

