# backend/metrics/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sla.calendar_engine import get_calendar
from tickets_t.permissions import IsAdmin, IsAgent

from . import services


class AdminMetricsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.organization is None:
            return Response({"detail": "Sin organización."}, status=404)
        window = services._parse_window(request)
        cal = get_calendar(request.organization)
        qs = services.windowed_tickets(window, request.organization)
        return Response({
            "window": window,
            "totals": services.volume_totals(qs),
            "compliance": services.compliance(qs),
            "avg_times": services.avg_times(qs, cal),
            "csat": services.csat_summary(qs),
            "trend": services.trend(qs, window),
            "ranking": services.technician_ranking(qs, cal),
        })


class MyMetricsView(APIView):
    permission_classes = [IsAuthenticated, IsAgent]

    def get(self, request):
        if request.organization is None:
            return Response({"detail": "Sin organización."}, status=404)
        window = services._parse_window(request)
        cal = get_calendar(request.organization)
        team = services.windowed_tickets(window, request.organization)
        mine = team.filter(asignado_a=request.user)
        return Response({
            "window": window,
            "totals": services.volume_totals(mine),
            "compliance": services.compliance(mine),
            "avg_times": services.avg_times(mine, cal),
            "csat": services.csat_summary(mine),
            "trend": services.trend(mine, window),
            "benchmark": {
                "compliance": services.compliance(team),
                "avg_times": services.avg_times(team, cal),
                "csat": {"average": services.csat_summary(team)["average"]},
            },
        })
