from django.urls import path
from . import public_views as v
from .contact_view import ContactView

urlpatterns = [
    path("landing/hero/", v.HeroPublicView.as_view()),
    path("landing/about/", v.AboutPublicView.as_view()),
    path("site-settings/", v.SiteSettingsPublicView.as_view()),
    path("landing/features/", v.FeatureListView.as_view()),
    path("landing/team/", v.TeamListView.as_view()),
    path("landing/locations/", v.LocationListView.as_view()),
    path("contact/", ContactView.as_view()),
]
