import threading

from django.conf import settings
from django.core.mail import send_mail


def _base():
    return getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")


def _send(subject, body, to):
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=True)


def _dispatch(subject, body, to):
    if getattr(settings, "NOTIFICATIONS_EMAIL_ASYNC", True):
        threading.Thread(target=_send, args=(subject, body, to), daemon=True).start()
    else:
        _send(subject, body, to)


def send_verification_email(user, token):
    link = f"{_base()}/verificar/{token}"
    _dispatch(
        "Confirmá tu cuenta en AllSafe",
        f"Hola {user.first_name or ''},\n\nConfirmá tu email para activar tu cuenta:\n{link}\n\n"
        "El enlace vence en 48 horas.",
        user.email,
    )


def send_invitation_email(invitation):
    link = f"{_base()}/invitacion/{invitation.token}"
    _dispatch(
        f"Te invitaron a {invitation.organization.name} en AllSafe",
        f"Te invitaron a unirte a {invitation.organization.name}.\n\n"
        f"Aceptá la invitación y creá tu contraseña:\n{link}\n\nEl enlace vence en 7 días.",
        invitation.email,
    )
