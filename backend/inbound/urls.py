from django.urls import path

from .views import WhatsAppWebhookView, EmailWebhookView, MessengerWebhookView

urlpatterns = [
    path("whatsapp/", WhatsAppWebhookView.as_view(), name="inbound-whatsapp"),
    path("email/", EmailWebhookView.as_view(), name="inbound-email"),
    path("messenger/", MessengerWebhookView.as_view(), name="inbound-messenger"),
]
