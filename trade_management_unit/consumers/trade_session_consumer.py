from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
class TradeSession(WebsocketConsumer):
    def connect(self):
        print("In Consumer Now")
        self.room_name = "test_consumer"
        self.room_group_name = "test_consumer_group"
        async_to_sync(self.channel_layer.group_add)(
            self.room_name, self.room_group_name
        )
        self.accept()
        self.send(text_data = json.dumps({"status":"connected from channels now  "}))

    def disconnect(self, *args , **kwargs):
        print("Disconnected Now")


    def receive(self, text_data=None, bytes_data=None):
        # Handle received market update data and update UI or trigger trade actions.
        self.send(text_data = json.dumps({"recieved":text_data}))

    # async def send(self, text_data=None, bytes_data=None):
    #     # Send data to the client.
    #     pass
