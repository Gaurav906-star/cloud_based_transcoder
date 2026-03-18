from channels.generic.websocket import AsyncWebsocketConsumer
import json

class VideoConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        print("🔥 CONNECTED")   # debug

        await self.channel_layer.group_add(
            "videos_group",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        print("❌ DISCONNECTED")

        await self.channel_layer.group_discard(
            "videos_group",
            self.channel_name
        )

    async def send_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))