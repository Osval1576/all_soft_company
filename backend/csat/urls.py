from django.urls import path
from .views import SubmitCsatView

urlpatterns = [
    path("<int:ticket_id>/", SubmitCsatView.as_view()),
]
