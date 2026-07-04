import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .presence import mark_online, mark_offline


class NotifyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.user_id = user.id
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._mark_online()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "user_id"):
            await self._mark_offline()

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        if data.get("type") == "ping":
            await self._mark_online()

    async def notify_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    @database_sync_to_async
    def _mark_online(self):
        mark_online(self.user_id)

    @database_sync_to_async
    def _mark_offline(self):
        mark_offline(self.user_id)
