from django.conf import settings
from django.core.mail import send_mail


def send_notification_email(recipient, subject, body):
    email = getattr(recipient, "email", "")
    if not email:
        return
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=True,
    )
