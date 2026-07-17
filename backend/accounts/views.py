from django.db import IntegrityError
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from config.auth_views import cookie_settings, COOKIE_ACCESS_NAME, COOKIE_REFRESH_NAME
from tickets_t.permissions import IsAdmin
from .emails import send_verification_email, send_invitation_email
from .models import EmailVerificationToken, Invitation
from .serializers import RegisterSerializer, InvitationCreateSerializer, AcceptInvitationSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            user, token = ser.save()
        except IntegrityError:
            return Response(
                {"detail": "Ya existe una cuenta u organización con esos datos."}, status=400
            )
        send_verification_email(user, token.token)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        obj = EmailVerificationToken.objects.filter(token=token).select_related("user").first()
        if obj is None or not obj.is_valid():
            return Response({"detail": "Token inválido o vencido."}, status=400)
        from django.utils import timezone
        obj.user.is_active = True
        obj.user.save(update_fields=["is_active"])
        obj.used_at = timezone.now()
        obj.save(update_fields=["used_at"])
        return Response({"ok": True})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resend"

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.filter(email__iexact=email, is_active=False).first()
        if user is not None:
            EmailVerificationToken.objects.filter(user=user).delete()
            tok = EmailVerificationToken.objects.create(user=user)
            send_verification_email(user, tok.token)
        return Response({"ok": True})  # generico siempre (anti-enumeracion)


def _login_response(user, data, status_code=200):
    refresh = RefreshToken.for_user(user)
    resp = Response(data, status=status_code)
    opts = cookie_settings()
    resp.set_cookie(COOKIE_ACCESS_NAME, str(refresh.access_token), **opts)
    resp.set_cookie(COOKIE_REFRESH_NAME, str(refresh), **opts)
    return resp


class InvitationViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                        mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = InvitationCreateSerializer

    def get_queryset(self):
        return Invitation.objects.filter(
            organization=self.request.organization, status="pending").order_by("-created_at")

    def perform_create(self, serializer):
        inv = serializer.save(organization=self.request.organization,
                              invited_by=self.request.user)
        send_invitation_email(inv)

    def perform_destroy(self, instance):
        instance.status = Invitation.Status.REVOKED
        instance.save(update_fields=["status"])


class InvitationDetailView(APIView):
    """GET público: detalle de una invitación por token (para la pantalla de aceptación)."""
    permission_classes = [AllowAny]

    def get(self, request, token):
        inv = Invitation.objects.filter(token=token).select_related("organization").first()
        if inv is None or not inv.is_acceptable():
            return Response({"detail": "Invitación inválida o vencida."}, status=404)
        return Response({"organization": inv.organization.name, "role": inv.role,
                         "email": inv.email})


class AcceptInvitationView(APIView):
    """POST público: crea el usuario con el rol/org DEL TOKEN (nunca del body) y loguea."""
    permission_classes = [AllowAny]

    def post(self, request, token):
        inv = Invitation.objects.filter(token=token).select_related("organization").first()
        if inv is None or not inv.is_acceptable():
            return Response({"detail": "Invitación inválida o vencida."}, status=410)
        ser = AcceptInvitationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from django.contrib.auth import get_user_model
        from django.db import transaction
        with transaction.atomic():
            user = get_user_model()(
                username=inv.email, email=inv.email,
                first_name=ser.validated_data["first_name"],
                last_name=ser.validated_data.get("last_name", ""),
                role=inv.role, organization=inv.organization, is_active=True)
            user.set_password(ser.validated_data["password"])
            user.save()
            inv.status = Invitation.Status.ACCEPTED
            inv.save(update_fields=["status"])
        return _login_response(user, {"ok": True})
