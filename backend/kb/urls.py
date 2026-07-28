from django.urls import path

from .deflect_view import DeflectView

urlpatterns = [
    path("deflect/", DeflectView.as_view(), name="kb-deflect"),
]
