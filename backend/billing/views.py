# backend/billing/views.py
from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets_t.permissions import IsAdmin
from . import stripe_gateway
from .models import Plan, ProcessedStripeEvent, Subscription
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


class WebhookView(APIView):
    """Superficie pública, firmada. Única fuente de verdad del estado de pago:
    ningún otro endpoint muta Subscription.status a partir de datos del cliente."""
    permission_classes = [AllowAny]

    def post(self, request):
        sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe_gateway.verify_and_parse_webhook(request.body, sig)
        except Exception:
            return Response({"detail": "Firma inválida."}, status=400)
        eid = event["id"] if isinstance(event, dict) else event.id
        if ProcessedStripeEvent.objects.filter(event_id=eid).exists():
            return Response({"ok": True})  # ya procesado (idempotencia)
        _handle_event(event)
        ProcessedStripeEvent.objects.get_or_create(event_id=eid)
        return Response({"ok": True})


def _obj(event, key):
    return (event["data"]["object"].get(key) if isinstance(event, dict)
            else getattr(event.data.object, key, None))


def _etype(event):
    return event["type"] if isinstance(event, dict) else event.type


def _handle_event(event):
    et = _etype(event)
    if et == "checkout.session.completed":
        org_id = _obj(event, "client_reference_id")
        sub = Subscription.objects.filter(organization_id=org_id).first()
        if sub is None:
            return
        sub.status = Subscription.Status.ACTIVE
        sub.stripe_customer_id = _obj(event, "customer") or sub.stripe_customer_id
        sub.stripe_subscription_id = _obj(event, "subscription") or sub.stripe_subscription_id
        sub.save()
    elif et in ("customer.subscription.updated", "customer.subscription.deleted"):
        stripe_sub_id = _obj(event, "id")
        sub = Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).first()
        if sub is None:
            return
        if et == "customer.subscription.deleted":
            free = Plan.objects.filter(key="free").first()
            if free:
                sub.plan = free
            sub.status = Subscription.Status.CANCELED
            sub.save()
        else:
            sub.status = Subscription.Status.ACTIVE
            sub.save()
    elif et == "invoice.payment_failed":
        stripe_sub_id = _obj(event, "subscription")
        sub = Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).first()
        if sub:
            sub.status = Subscription.Status.PAST_DUE
            sub.save()
