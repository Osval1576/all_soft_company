from django.contrib import admin

from .models import EmailVerificationToken, Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "role", "status", "created_at", "expires_at")
    list_filter = ("status", "role")
    search_fields = ("email", "organization__name")


admin.site.register(EmailVerificationToken)
