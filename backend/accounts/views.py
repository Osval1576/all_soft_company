from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .emails import send_verification_email
from .models import EmailVerificationToken
from .serializers import RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user, token = ser.save()
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
