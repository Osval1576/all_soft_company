from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from tickets_t.models import Ticket, TicketMessage

from .serializers import ContactSerializer

User = get_user_model()


def _next_reference():
    prefix = "ALS-" + datetime.utcnow().strftime("%Y%m%d") + "-"
    last = (
        Ticket.objects.select_for_update()
        .filter(reference__startswith=prefix)
        .order_by("-reference")
        .first()
    )
    n = int(last.reference.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{n:06d}"


class ContactView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    @transaction.atomic
    def post(self, request):
        ser = ContactSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        if data.get("website"):
            return Response({"ok": True})

        user = User.objects.filter(email=data["email"]).first()
        if user is None:
            user = User(
                username=data["email"],
                email=data["email"],
                first_name=data["name"][:30],
                role="CUSTOMER",
            )
            user.set_unusable_password()
            try:
                user.save()
            except IntegrityError:
                user = User.objects.get(email=data["email"])

        ticket = Ticket.objects.create(
            reference=_next_reference(),
            titulo=data["subject"],
            descripcion=data["message"],
            prioridad="MEDIUM",
            estado="OPEN",
            creado_por=user,
        )
        TicketMessage.objects.create(
            ticket=ticket, sender=user, content=data["message"],
        )
        return Response({"ticket_reference": ticket.reference},
                        status=status.HTTP_201_CREATED)
