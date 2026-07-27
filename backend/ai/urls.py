from django.urls import path

from .views import TicketAiDraftView

urlpatterns = [
    path("tickets/<int:ticket_id>/draft/", TicketAiDraftView.as_view(), name="ai-ticket-draft"),
]
