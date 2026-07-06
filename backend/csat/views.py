from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets_t.models import Ticket

from .eligibility import is_eligible
from .models import CSATResponse
from .payloads import csat_payload
from .serializers import CSATSubmitSerializer


class SubmitCsatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        ticket = Ticket.objects.filter(pk=ticket_id).first()
        if ticket is None:
            return Response({"detail": "No encontrado."}, status=404)
        if ticket.creado_por_id != request.user.id:
            return Response({"detail": "Solo el creador del ticket puede calificar."}, status=403)
        if not is_eligible(ticket):
            return Response({"detail": "El ticket todavía no está resuelto."}, status=400)
        if getattr(ticket, "csat", None) is not None:
            return Response({"detail": "Ya calificaste este ticket."}, status=409)

        ser = CSATSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        CSATResponse.objects.create(ticket=ticket, **ser.validated_data)
        return Response(csat_payload(ticket), status=201)
