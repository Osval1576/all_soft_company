from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from tenancy.scoping import org_tickets
from tickets_t.models import TicketMessage

from .serializers import ContactSerializer

User = get_user_model()


def _als_org():
    # El formulario publico de contacto no tiene organizacion (es anonimo, sin
    # request.organization): sus tickets son siempre de ALS/"AllSafe", la org
    # semilla de la plataforma (mismo prefijo "ALS-" que ya usaba la referencia
    # antes de multi-tenant). get_or_create la autocura si faltara.
    from tenancy.models import Organization
    org, _ = Organization.objects.get_or_create(slug="ALS", defaults={"name": "AllSafe"})
    return org


def _next_reference():
    prefix = "ALS-" + timezone.now().strftime("%Y%m%d") + "-"
    last = (
        org_tickets(_als_org()).select_for_update()
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
                organization=_als_org(),  # el submitter anonimo pertenece a la org semilla
            )
            user.set_unusable_password()
            try:
                user.save()
            except IntegrityError:
                user = User.objects.get(username=data["email"])

        for attempt in range(3):
            try:
                with transaction.atomic():
                    ticket = org_tickets(_als_org()).create(
                        reference=_next_reference(),
                        titulo=data["subject"],
                        descripcion=data["message"],
                        prioridad="MEDIUM",
                        estado="OPEN",
                        creado_por=user,
                        organization=_als_org(),
                    )
                break
            except IntegrityError:
                if attempt == 2:
                    raise
                continue
        else:
            raise IntegrityError("could not allocate ticket reference after 3 attempts")

        TicketMessage.objects.create(
            ticket=ticket, sender=user, content=data["message"],
        )
        return Response({"ticket_reference": ticket.reference},
                        status=status.HTTP_201_CREATED)
