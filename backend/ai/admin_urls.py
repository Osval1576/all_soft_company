from django.urls import path

from .admin_views import OrgAiSettingsView

urlpatterns = [
    path("settings/", OrgAiSettingsView.as_view(), name="ai-admin-settings"),
]
