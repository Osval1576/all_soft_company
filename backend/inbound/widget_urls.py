from django.urls import path

from .widget_views import WidgetAskView, WidgetContactView

urlpatterns = [
    path("<str:key>/ask/", WidgetAskView.as_view(), name="widget-ask"),
    path("<str:key>/contact/", WidgetContactView.as_view(), name="widget-contact"),
]
