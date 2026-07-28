from django.db import models


class Channel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"
    INSTAGRAM = "instagram", "Instagram"
    WIDGET = "widget", "Widget web"


class ChannelAccount(models.Model):
    """Mapea una cuenta externa de un canal (p. ej. el phone_number_id de WhatsApp
    o el buzón de email) a una organización. La ingesta usa el identificador que
    viene en el webhook para saber a qué tenant pertenece el mensaje.
    """
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="channel_accounts")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    external_id = models.CharField(max_length=255)  # phone_number_id / email / page id
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Un mismo identificador de canal enruta a UNA sola org.
            models.UniqueConstraint(fields=["channel", "external_id"],
                                    name="uniq_channel_external_id"),
        ]

    def __str__(self):
        return f"{self.channel}:{self.external_id} -> org {self.organization_id}"


class ChannelThread(models.Model):
    """Hilo de un contacto externo en un canal, ligado a su ticket actual. Sirve
    para que los mensajes sucesivos del mismo contacto caigan en el mismo ticket
    (mientras siga abierto)."""
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="channel_threads")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    contact_external_id = models.CharField(max_length=255)  # nº de teléfono / email del cliente
    ticket = models.ForeignKey(
        "tickets_t.Ticket", on_delete=models.CASCADE, related_name="channel_threads")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "channel", "contact_external_id"],
                                    name="uniq_thread_per_contact"),
        ]

    def __str__(self):
        return f"{self.channel}:{self.contact_external_id} (org {self.organization_id})"
