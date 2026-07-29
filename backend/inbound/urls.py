from django.urls import path

from .views import WhatsAppWebhookView, EmailWebhookView

urlpatterns = [
    path("whatsapp/", WhatsAppWebhookView.as_view(), name="inbound-whatsapp"),
    path("email/", EmailWebhookView.as_view(), name="inbound-email"),
]
