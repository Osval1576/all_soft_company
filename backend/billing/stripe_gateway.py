# backend/billing/stripe_gateway.py
"""Wrapper aislado de la API de Stripe (unico modulo que la importa/llama).
Aislado para (a) mockear en tests y (b) degradar sin claves."""
from django.conf import settings


def is_configured():
    return bool(getattr(settings, "STRIPE_SECRET_KEY", ""))


def _client():
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _ensure_customer(subscription):
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id
    stripe = _client()
    customer = stripe.Customer.create(name=subscription.organization.name)
    subscription.stripe_customer_id = customer.id
    subscription.save(update_fields=["stripe_customer_id"])
    return customer.id


def create_checkout_session(subscription, plan, success_url, cancel_url):
    stripe = _client()
    customer_id = _ensure_customer(subscription)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(subscription.organization_id),
    )
    return session.url


def create_portal_session(subscription, return_url):
    stripe = _client()
    session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id, return_url=return_url)
    return session.url


def verify_and_parse_webhook(payload, sig_header):
    """Devuelve el evento verificado o lanza ValueError/SignatureVerificationError."""
    stripe = _client()
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
