from django.urls import path

from .views import TicketAiDraftView, TicketAiSummaryView, InsightsView, TranslateView

urlpatterns = [
    path("tickets/<int:ticket_id>/draft/", TicketAiDraftView.as_view(), name="ai-ticket-draft"),
    path("tickets/<int:ticket_id>/summary/", TicketAiSummaryView.as_view(), name="ai-ticket-summary"),
    path("insights/", InsightsView.as_view(), name="ai-insights"),
    path("translate/", TranslateView.as_view(), name="ai-translate"),
]
