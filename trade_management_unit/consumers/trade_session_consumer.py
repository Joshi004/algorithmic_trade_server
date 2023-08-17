from channels.generic.websocket import WebsocketConsumer,AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
import json
class TradeSession(AsyncWebsocketConsumer):
    async def connect(self):
        print("In Consumer Now")
        self.room_name = "test_consumer"
        self.room_group_name = "test_consumer_group"
        await (self.channel_layer.group_add)(
            self.room_name, self.room_group_name
        )
        await self.accept()
        await self.send(text_data = json.dumps({"status":"connected from channels now  "}))

    async def disconnect(self, *args , **kwargs):
        print("Disconnected Now")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)


    async def receive(self, text_data=None, bytes_data=None):
        # Handle received market update data and update UI or trigger trade actions.
        await self.send(text_data = json.dumps({"recieved":text_data}))

    # async def send(self, text_data=None, bytes_data=None):
    #     # Send data to the client.
    #     pass
