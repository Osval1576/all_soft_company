from django.urls import path

from .views import (
    RegisterView, VerifyEmailView, ResendVerificationView,
    InvitationDetailView, AcceptInvitationView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("invitation/<str:token>/", InvitationDetailView.as_view(), name="invitation-public"),
    path("invitation/<str:token>/accept/", AcceptInvitationView.as_view(), name="invitation-accept"),
]
