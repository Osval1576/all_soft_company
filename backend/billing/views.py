# backend/billing/views.py
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets_t.permissions import IsAdmin
from . import stripe_gateway
from .models import Plan
from .services import active_agent_count, agent_limit


def _plans_payload():
    return [{"key": p.key, "name": p.name, "max_agents": p.max_agents, "order": p.order}
            for p in Plan.objects.filter(is_active=True)]


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        org = request.organization
        sub = org.subscription
        return Response({
            "plan": sub.effective_plan.key,
            "plan_name": sub.effective_plan.name,
            "status": sub.status,
            "trial_ends_at": sub.trial_ends_at,
            "current_period_end": sub.current_period_end,
            "agent_count": active_agent_count(org),
            "agent_limit": agent_limit(org),
            "plans": _plans_payload(),
        })


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        if not stripe_gateway.is_configured():
            return Response({"detail": "Billing no configurado."}, status=503)
        plan = Plan.objects.filter(key=request.data.get("plan_key"), is_active=True).first()
        if plan is None or plan.key == "free":
            return Response({"detail": "Plan inválido para pago."}, status=400)
        base = settings.FRONTEND_BASE_URL.rstrip("/")
        url = stripe_gateway.create_checkout_session(
            request.organization.subscription, plan,
            f"{base}/admin/suscripcion?success=1", f"{base}/admin/suscripcion?canceled=1")
        return Response({"url": url})


class PortalView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        sub = request.organization.subscription
        if not stripe_gateway.is_configured() or not sub.stripe_customer_id:
            return Response({"detail": "Billing no configurado."}, status=503)
        base = settings.FRONTEND_BASE_URL.rstrip("/")
        url = stripe_gateway.create_portal_session(sub, f"{base}/admin/suscripcion")
        return Response({"url": url})
