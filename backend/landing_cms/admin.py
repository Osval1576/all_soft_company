from django.contrib import admin
from .models import (
    HeroContent, AboutContent, SiteSettings,
    Feature, TeamMember, Location,
)


@admin.register(HeroContent)
class HeroAdmin(admin.ModelAdmin):
    pass


@admin.register(AboutContent)
class AboutAdmin(admin.ModelAdmin):
    pass


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    pass


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("title_es", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role_es", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "order", "is_active")
    list_editable = ("order", "is_active")
