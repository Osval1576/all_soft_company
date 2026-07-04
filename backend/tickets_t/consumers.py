import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .models import Ticket, TicketMessage


class TicketChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.ticket_id = int(self.scope["url_route"]["kwargs"]["ticket_id"])
        allowed = await self.user_can_access_ticket(user.id, self.ticket_id)
        if not allowed:
            await self.close(code=4403)
            return

        self.group_name = f"ticket_{self.ticket_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope["user"]
        data = json.loads(text_data or "{}")
        content = (data.get("content") or "").strip()
        if not content:
            return

        msg = await self.create_message(user.id, self.ticket_id, content)

        payload = {
            "type": "chat.message",
            "message": {
                "id": msg["id"],
                "ticket": self.ticket_id,
                "sender": msg["sender_id"],
                "sender_username": msg["sender_username"],
                "sender_role": msg["sender_role"],
                "content": msg["content"],
                "created_at": msg["created_at"],
            },
        }
        await self.channel_layer.group_send(self.group_name, payload)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    # ---- DB helpers ----

    @database_sync_to_async
    def user_can_access_ticket(self, user_id, ticket_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            ticket = Ticket.objects.select_related("creado_por", "asignado_a").get(id=ticket_id)
            user = User.objects.get(id=user_id)
        except (Ticket.DoesNotExist, User.DoesNotExist):
            return False

        r = getattr(user, "role", None)
        if r == "ADMIN" or user.is_superuser:
            return True
        if r == "CUSTOMER":
            return ticket.creado_por_id == user_id
        if r == "AGENT":
            return ticket.asignado_a_id == user_id
        return False

    @database_sync_to_async
    def create_message(self, user_id, ticket_id, content):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        ticket = Ticket.objects.get(id=ticket_id)

        m = TicketMessage.objects.create(
            ticket=ticket,
            sender=user,
            content=content,
        )
        from notifications.services import dispatch
        dispatch("new_message", ticket, actor=user, extra={"content": content})
        return {
            "id": m.id,
            "sender_id": user.id,
            "sender_username": user.username,
            "sender_role": getattr(user, "role", None),
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
