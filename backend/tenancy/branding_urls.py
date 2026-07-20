from django.urls import path
from .branding_views import BrandingView

urlpatterns = [
    path("", BrandingView.as_view(), name="branding"),
]
