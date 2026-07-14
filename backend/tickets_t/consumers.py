import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .models import Ticket, TicketMessage
from .payloads import message_to_payload
from .permissions import can_access_ticket

logger = logging.getLogger(__name__)


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

        message = await self.create_message(user.id, self.ticket_id, content)
        # el path de texto por WS nunca lleva adjunto: se quita la key para
        # mantener el shape historico del payload byte-identico
        message.pop("attachment", None)

        payload = {
            "type": "chat.message",
            "message": message,
        }
        await self.channel_layer.group_send(self.group_name, payload)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    # ---- DB helpers ----

    @database_sync_to_async
    def user_can_access_ticket(self, user_id, ticket_id):
        from django.contrib.auth import get_user_model
        from tenancy.scoping import org_tickets
        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
            # Scoped por la org del usuario: un ticket de otra org ni siquiera
            # aparece en el queryset (Ticket.DoesNotExist -> acceso denegado),
            # sin depender solo del chequeo de org en can_access_ticket.
            ticket = org_tickets(user.organization).select_related(
                "creado_por", "asignado_a").get(id=ticket_id)
        except (Ticket.DoesNotExist, User.DoesNotExist):
            return False

        return can_access_ticket(user, ticket)

    @database_sync_to_async
    def create_message(self, user_id, ticket_id, content):
        from django.contrib.auth import get_user_model
        from tenancy.scoping import org_tickets
        User = get_user_model()
        user = User.objects.get(id=user_id)
        ticket = org_tickets(user.organization).get(id=ticket_id)

        m = TicketMessage.objects.create(
            ticket=ticket,
            sender=user,
            content=content,
        )
        from notifications.services import dispatch
        try:
            dispatch("new_message", ticket, actor=user, extra={"content": content})
        except Exception:
            logger.exception("notification dispatch failed for ticket %s", self.ticket_id)
        return message_to_payload(m)
