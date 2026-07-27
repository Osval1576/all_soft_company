from django.urls import path

from .views import TicketAiDraftView, TicketAiSummaryView

urlpatterns = [
    path("tickets/<int:ticket_id>/draft/", TicketAiDraftView.as_view(), name="ai-ticket-draft"),
    path("tickets/<int:ticket_id>/summary/", TicketAiSummaryView.as_view(), name="ai-ticket-summary"),
]
