"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView,
)
from .views import me, health, csrf
from .auth_views import (
    LoginCookieView, RefreshCookieView, LogoutView, ThrottledTokenObtainPairView,
)
from landing_cms.admin_views import SiteSettingsAdminView
from tenancy.branding_views import PublicBrandingView
from inbound.widget_views import widget_script

v_settings_admin = SiteSettingsAdminView.as_view()

urlpatterns = [
    path("django-admin/", admin.site.urls),

    path("api/auth/", include("accounts.urls")),
    path("api/auth/login/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/me/", me, name="me"),
    path("api/health/", health, name="health"),

    # Documentación de API: esquema OpenAPI 3 + UIs Swagger y Redoc.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    path("api/users/", include("users.urls")),
    path("api/invitations/", include("accounts.invitation_urls")),
    path("api/public/", include("landing_cms.public_urls")),
    path("api/admin/landing/", include("landing_cms.admin_urls")),
    path("api/admin/site-settings/", v_settings_admin),
    path("api/admin/sla/", include("sla.admin_urls")),
    path("api/admin/kb/", include("kb.admin_urls")),
    path("api/admin/inbound/", include("inbound.admin_urls")),
    path("api/admin/ai/", include("ai.admin_urls")),
    path("api/", include("tickets_t.urls")),
    path("api/", include("notifications.urls")),
    path("api/csat/", include("csat.urls")),
    path("api/metrics/", include("metrics.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/ai/", include("ai.urls")),
    path("api/kb/", include("kb.urls")),
    path("api/inbound/", include("inbound.urls")),
    path("api/widget/", include("inbound.widget_urls")),
    path("widget.js", widget_script, name="widget-js"),
    path("api/branding/", include("tenancy.branding_urls")),
    path("api/public/branding/<str:slug>/", PublicBrandingView.as_view(), name="public-branding"),
    path("api/auth/login-cookie/", LoginCookieView.as_view(), name="login_cookie"),
    path("api/auth/refresh-cookie/", RefreshCookieView.as_view(), name="refresh_cookie"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/csrf/", csrf, name="csrf"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

