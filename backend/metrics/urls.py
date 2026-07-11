# backend/metrics/urls.py
from django.urls import path
from .views import AdminMetricsView, MyMetricsView

urlpatterns = [
    path("admin/", AdminMetricsView.as_view(), name="metrics-admin"),
    path("me/", MyMetricsView.as_view(), name="metrics-me"),
]
