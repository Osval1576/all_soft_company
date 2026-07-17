from django.conf import settings
from django.core.mail import send_mail


def _base():
    return getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")


def send_verification_email(user, token):
    link = f"{_base()}/verificar/{token}"
    send_mail(
        "Confirmá tu cuenta en AllSafe",
        f"Hola {user.first_name or ''},\n\nConfirmá tu email para activar tu cuenta:\n{link}\n\n"
        "El enlace vence en 48 horas.",
        settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False,
    )


def send_invitation_email(invitation):
    link = f"{_base()}/invitacion/{invitation.token}"
    send_mail(
        f"Te invitaron a {invitation.organization.name} en AllSafe",
        f"Te invitaron a unirte a {invitation.organization.name}.\n\n"
        f"Aceptá la invitación y creá tu contraseña:\n{link}\n\nEl enlace vence en 7 días.",
        settings.DEFAULT_FROM_EMAIL, [invitation.email], fail_silently=False,
    )
