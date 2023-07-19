from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import asyn_to_sync
import json

class TestConsumer(WebSocketConsumer):
    #ws://
    def connect(self):
        print("In Consumer Now")
        self.room_name = "test_consumer"
        self.room_group_name = "test_consumer_group"
        async_to_sync(self.channel_layer.group.add)(
            self.room_name, self.room_group_name
        )
        self.accept()
        self.send(text_data = json.dumps({"status":"connected"}))

    def receive(self, text_data):
        pass

    def disconnect(self, close_code):
        pass


    