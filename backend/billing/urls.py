# backend/billing/urls.py
from django.urls import path
from .views import SubscriptionView, CheckoutView, PortalView

urlpatterns = [
    path("subscription/", SubscriptionView.as_view(), name="subscription"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("portal/", PortalView.as_view(), name="portal"),
]
